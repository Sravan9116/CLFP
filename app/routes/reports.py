from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from app.extensions import db
from app.models.report import LostReport, FoundReport, ItemCategory, CampusLocation, ReportImage
from app.models.match import ItemMatch
from app.models.notification import AuditLog
from app.services.image_service import process_and_save_image
from app.services.notification_service import notify_admins, create_notification
from app.services.matching_service import evaluate_and_store_matches

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

def generate_report_code(report_type):
    year = datetime.utcnow().year
    if report_type == 'lost':
        count = LostReport.query.count() + 1
        return f"LOST-{year}-{count:05d}"
    else:
        count = FoundReport.query.count() + 1
        return f"FOUND-{year}-{count:05d}"

@reports_bp.route('')
def index():
    tab = request.args.get('tab', 'all')  # 'all', 'lost', 'found', 'my_reports', 'matches'
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category')
    location_id = request.args.get('location')
    color = request.args.get('color', '').strip()
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    sort_by = request.args.get('sort', 'latest')  # 'latest', 'oldest', 'name'
    page = request.args.get('page', 1, type=int)
    per_page = 12

    categories = ItemCategory.query.filter_by(status='active').order_by(ItemCategory.category_name).all()
    locations = CampusLocation.query.filter_by(status='active').order_by(CampusLocation.location_name).all()

    lost_query = LostReport.query.filter_by(review_status='approved')
    found_query = FoundReport.query.filter_by(review_status='approved')

    # Apply search filter
    if q:
        search_filter = or_(
            LostReport.item_name.ilike(f'%{q}%'),
            LostReport.description.ilike(f'%{q}%'),
            LostReport.brand.ilike(f'%{q}%'),
            LostReport.report_code.ilike(f'%{q}%')
        )
        lost_query = lost_query.filter(search_filter)
        
        found_search_filter = or_(
            FoundReport.item_name.ilike(f'%{q}%'),
            FoundReport.description.ilike(f'%{q}%'),
            FoundReport.brand.ilike(f'%{q}%'),
            FoundReport.report_code.ilike(f'%{q}%')
        )
        found_query = found_query.filter(found_search_filter)

    # Category filter
    if category_id and category_id.isdigit():
        lost_query = lost_query.filter_by(category_id=int(category_id))
        found_query = found_query.filter_by(category_id=int(category_id))

    # Location filter
    if location_id and location_id.isdigit():
        lost_query = lost_query.filter_by(location_id=int(location_id))
        found_query = found_query.filter_by(location_id=int(location_id))

    # Color filter
    if color:
        lost_query = lost_query.filter(or_(
            LostReport.primary_color.ilike(f'%{color}%'),
            LostReport.secondary_color.ilike(f'%{color}%')
        ))
        found_query = found_query.filter(or_(
            FoundReport.primary_color.ilike(f'%{color}%'),
            FoundReport.secondary_color.ilike(f'%{color}%')
        ))

    # Date filter
    if date_from:
        try:
            d_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            lost_query = lost_query.filter(LostReport.date_lost >= d_from)
            found_query = found_query.filter(FoundReport.date_found >= d_from)
        except ValueError:
            pass
            
    if date_to:
        try:
            d_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            lost_query = lost_query.filter(LostReport.date_lost <= d_to)
            found_query = found_query.filter(FoundReport.date_found <= d_to)
        except ValueError:
            pass

    # Sort
    if sort_by == 'oldest':
        lost_query = lost_query.order_by(LostReport.created_at.asc())
        found_query = found_query.order_by(FoundReport.created_at.asc())
    elif sort_by == 'name':
        lost_query = lost_query.order_by(LostReport.item_name.asc())
        found_query = found_query.order_by(FoundReport.item_name.asc())
    else:
        lost_query = lost_query.order_by(LostReport.created_at.desc())
        found_query = found_query.order_by(FoundReport.created_at.desc())

    # User personal reports & matches
    user_lost_reports = []
    user_found_reports = []
    potential_matches = []
    if current_user.is_authenticated:
        user_lost_reports = LostReport.query.filter_by(user_id=current_user.id).order_by(LostReport.created_at.desc()).all()
        user_found_reports = FoundReport.query.filter_by(user_id=current_user.id).order_by(FoundReport.created_at.desc()).all()
        
        user_lost_ids = [r.id for r in user_lost_reports]
        if user_lost_ids:
            potential_matches = ItemMatch.query.filter(
                ItemMatch.lost_report_id.in_(user_lost_ids),
                ItemMatch.match_score >= 40.0
            ).order_by(ItemMatch.match_score.desc()).all()

    # Results by tab
    if tab == 'lost':
        pagination = lost_query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items
    elif tab == 'found':
        pagination = found_query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items
    elif tab == 'my_reports':
        pagination = None
        items = user_lost_reports + user_found_reports
    elif tab == 'matches':
        pagination = None
        items = potential_matches
    else:
        # All items: combine lost and found
        lost_items = lost_query.all()
        found_items = found_query.all()
        all_combined = sorted(lost_items + found_items, key=lambda x: x.created_at, reverse=(sort_by != 'oldest'))
        
        total = len(all_combined)
        start = (page - 1) * per_page
        end = start + per_page
        items = all_combined[start:end]
        
        # Simple custom pagination proxy for all items
        class PaginationProxy:
            def __init__(self, page, per_page, total):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = max(1, (total + per_page - 1) // per_page)
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1
                self.next_num = page + 1
        pagination = PaginationProxy(page, per_page, total)

    return render_template(
        'reports/list.html',
        items=items,
        pagination=pagination,
        tab=tab,
        categories=categories,
        locations=locations,
        q=q,
        selected_category=category_id,
        selected_location=location_id,
        selected_color=color,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        user_lost_count=len(user_lost_reports),
        user_found_count=len(user_found_reports),
        potential_matches_count=len(potential_matches)
    )

@reports_bp.route('/lost/new', methods=['GET', 'POST'])
@login_required
def report_lost():
    categories = ItemCategory.query.filter_by(status='active').order_by(ItemCategory.category_name).all()
    locations = CampusLocation.query.filter_by(status='active').order_by(CampusLocation.location_name).all()

    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        brand = request.form.get('brand', '').strip()
        primary_color = request.form.get('primary_color', '').strip()
        secondary_color = request.form.get('secondary_color', '').strip()
        date_lost_str = request.form.get('date_lost')
        approximate_time = request.form.get('approximate_time', '').strip()
        location_id = request.form.get('location_id')
        additional_location = request.form.get('additional_location', '').strip()
        identifying_features = request.form.get('identifying_features', '').strip()
        contact_preference = request.form.get('contact_preference', 'email')

        if not item_name or not category_id or not description or not primary_color or not date_lost_str or not location_id:
            flash('Please complete all mandatory report fields.', 'danger')
            return render_template('reports/report_lost.html', categories=categories, locations=locations)

        try:
            date_lost = datetime.strptime(date_lost_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('reports/report_lost.html', categories=categories, locations=locations)

        # Process image upload safely
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                image_path = process_and_save_image(file, subfolder='reports')

        report_code = generate_report_code('lost')

        report = LostReport(
            report_code=report_code,
            user_id=current_user.id,
            category_id=int(category_id),
            item_name=item_name,
            description=description,
            brand=brand,
            primary_color=primary_color,
            secondary_color=secondary_color,
            date_lost=date_lost,
            approximate_time=approximate_time,
            location_id=int(location_id),
            additional_location=additional_location,
            image_path=image_path,
            identifying_features=identifying_features,
            contact_preference=contact_preference,
            review_status='pending_review',
            report_status='active'
        )
        db.session.add(report)
        db.session.flush()

        if image_path:
            img_record = ReportImage(
                report_type='lost',
                report_id=report.id,
                image_path=image_path
            )
            db.session.add(img_record)

        audit = AuditLog(
            actor_id=current_user.id,
            action='lost_report_submitted',
            entity_type='report',
            entity_id=str(report.id),
            details=f"User {current_user.full_name} submitted lost report {report_code} for '{item_name}'."
        )
        db.session.add(audit)
        db.session.commit()

        # Notify Administrators of new submission
        notify_admins(
            title="New Lost Item Report Awaiting Review",
            message=f"{current_user.full_name} reported lost item '{item_name}' ({report_code}).",
            notification_type='admin_alert',
            link_url=f"/admin/reports?type=lost&q={report_code}",
            related_report_id=report.id
        )

        create_notification(
            user_id=current_user.id,
            title="Lost Item Report Submitted",
            message=f"Your lost report {report_code} for '{item_name}' was received. It is pending administrative approval before appearing in public discovery.",
            notification_type='report_status',
            link_url=f"/reports/lost/{report.id}",
            related_report_id=report.id
        )

        flash(f'Report {report_code} submitted successfully! Our administrators will review and approve it shortly.', 'success')
        return redirect(url_for('reports.view_lost', id=report.id))

    return render_template('reports/report_lost.html', categories=categories, locations=locations)

@reports_bp.route('/found/new', methods=['GET', 'POST'])
@login_required
def report_found():
    categories = ItemCategory.query.filter_by(status='active').order_by(ItemCategory.category_name).all()
    locations = CampusLocation.query.filter_by(status='active').order_by(CampusLocation.location_name).all()

    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        brand = request.form.get('brand', '').strip()
        primary_color = request.form.get('primary_color', '').strip()
        secondary_color = request.form.get('secondary_color', '').strip()
        date_found_str = request.form.get('date_found')
        approximate_time = request.form.get('approximate_time', '').strip()
        location_id = request.form.get('location_id')
        custody_status = request.form.get('custody_status', 'finder_possession')
        custody_location = request.form.get('custody_location', '').strip()
        identifying_features = request.form.get('identifying_features', '').strip()

        if not item_name or not category_id or not description or not primary_color or not date_found_str or not location_id:
            flash('Please complete all mandatory report fields.', 'danger')
            return render_template('reports/report_found.html', categories=categories, locations=locations)

        try:
            date_found = datetime.strptime(date_found_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('reports/report_found.html', categories=categories, locations=locations)

        # Process image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                image_path = process_and_save_image(file, subfolder='reports')

        report_code = generate_report_code('found')

        report = FoundReport(
            report_code=report_code,
            user_id=current_user.id,
            category_id=int(category_id),
            item_name=item_name,
            description=description,
            brand=brand,
            primary_color=primary_color,
            secondary_color=secondary_color,
            date_found=date_found,
            approximate_time=approximate_time,
            location_id=int(location_id),
            custody_status=custody_status,
            custody_location=custody_location,
            image_path=image_path,
            identifying_features=identifying_features,
            review_status='pending_review',
            report_status='active'
        )
        db.session.add(report)
        db.session.flush()

        if image_path:
            img_record = ReportImage(
                report_type='found',
                report_id=report.id,
                image_path=image_path
            )
            db.session.add(img_record)

        audit = AuditLog(
            actor_id=current_user.id,
            action='found_report_submitted',
            entity_type='report',
            entity_id=str(report.id),
            details=f"User {current_user.full_name} submitted found report {report_code} for '{item_name}'."
        )
        db.session.add(audit)
        db.session.commit()

        # Notify Admins
        notify_admins(
            title="New Found Item Report Awaiting Review",
            message=f"{current_user.full_name} reported found item '{item_name}' ({report_code}).",
            notification_type='admin_alert',
            link_url=f"/admin/reports?type=found&q={report_code}",
            related_report_id=report.id
        )

        create_notification(
            user_id=current_user.id,
            title="Found Item Report Submitted",
            message=f"Thank you for reporting found item {report_code} ('{item_name}'). An administrator will review your report shortly.",
            notification_type='report_status',
            link_url=f"/reports/found/{report.id}",
            related_report_id=report.id
        )

        flash(f'Found item {report_code} reported! Thank you for helping our campus community.', 'success')
        return redirect(url_for('reports.view_found', id=report.id))

    return render_template('reports/report_found.html', categories=categories, locations=locations)

@reports_bp.route('/lost/<int:id>')
def view_lost(id):
    report = LostReport.query.get_or_404(id)
    
    # Check permissions for pending/rejected reports
    is_owner = current_user.is_authenticated and (current_user.id == report.user_id)
    is_admin = current_user.is_authenticated and current_user.is_admin
    
    if report.review_status != 'approved' and not (is_owner or is_admin):
        flash('This report is pending administrator review and is not publicly visible.', 'info')
        return redirect(url_for('reports.index'))
        
    # Potential matches for this lost report
    matches = []
    if is_owner or is_admin:
        matches = ItemMatch.query.filter_by(lost_report_id=report.id).filter(ItemMatch.match_score >= 40.0).order_by(ItemMatch.match_score.desc()).all()
        
    return render_template(
        'reports/detail.html',
        item=report,
        item_type='lost',
        is_owner=is_owner,
        is_admin=is_admin,
        matches=matches
    )

@reports_bp.route('/found/<int:id>')
def view_found(id):
    report = FoundReport.query.get_or_404(id)
    
    is_owner = current_user.is_authenticated and (current_user.id == report.user_id)
    is_admin = current_user.is_authenticated and current_user.is_admin
    
    if report.review_status != 'approved' and not (is_owner or is_admin):
        flash('This report is pending administrator review and is not publicly visible.', 'info')
        return redirect(url_for('reports.index'))
        
    # Check if current user already submitted a claim on this found item
    existing_claim = None
    if current_user.is_authenticated:
        from app.models.claim import Claim
        existing_claim = Claim.query.filter_by(
            found_report_id=report.id,
            claimant_id=current_user.id
        ).filter(Claim.claim_status.notin_(['cancelled'])).first()
        
    matches = []
    if is_owner or is_admin:
        matches = ItemMatch.query.filter_by(found_report_id=report.id).filter(ItemMatch.match_score >= 40.0).order_by(ItemMatch.match_score.desc()).all()
        
    return render_template(
        'reports/detail.html',
        item=report,
        item_type='found',
        is_owner=is_owner,
        is_admin=is_admin,
        matches=matches,
        existing_claim=existing_claim
    )

@reports_bp.route('/lost/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lost(id):
    report = LostReport.query.get_or_404(id)
    if report.user_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    categories = ItemCategory.query.filter_by(status='active').order_by(ItemCategory.category_name).all()
    locations = CampusLocation.query.filter_by(status='active').order_by(CampusLocation.location_name).all()
    
    if request.method == 'POST':
        report.item_name = request.form.get('item_name', report.item_name).strip()
        report.category_id = int(request.form.get('category_id', report.category_id))
        report.description = request.form.get('description', report.description).strip()
        report.brand = request.form.get('brand', '').strip()
        report.primary_color = request.form.get('primary_color', report.primary_color).strip()
        report.secondary_color = request.form.get('secondary_color', '').strip()
        report.location_id = int(request.form.get('location_id', report.location_id))
        report.additional_location = request.form.get('additional_location', '').strip()
        report.identifying_features = request.form.get('identifying_features', '').strip()
        report.contact_preference = request.form.get('contact_preference', 'email')
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                new_image = process_and_save_image(file, subfolder='reports')
                if new_image:
                    report.image_path = new_image
                    
        db.session.commit()
        
        # Trigger matching engine recalculation
        if report.review_status == 'approved':
            evaluate_and_store_matches(report, is_lost=True)
            
        flash('Report updated successfully.', 'success')
        return redirect(url_for('reports.view_lost', id=report.id))
        
    return render_template('reports/edit_report.html', report=report, report_type='lost', categories=categories, locations=locations)

@reports_bp.route('/found/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_found(id):
    report = FoundReport.query.get_or_404(id)
    if report.user_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    categories = ItemCategory.query.filter_by(status='active').order_by(ItemCategory.category_name).all()
    locations = CampusLocation.query.filter_by(status='active').order_by(CampusLocation.location_name).all()
    
    if request.method == 'POST':
        report.item_name = request.form.get('item_name', report.item_name).strip()
        report.category_id = int(request.form.get('category_id', report.category_id))
        report.description = request.form.get('description', report.description).strip()
        report.brand = request.form.get('brand', '').strip()
        report.primary_color = request.form.get('primary_color', report.primary_color).strip()
        report.secondary_color = request.form.get('secondary_color', '').strip()
        report.location_id = int(request.form.get('location_id', report.location_id))
        report.custody_status = request.form.get('custody_status', report.custody_status)
        report.custody_location = request.form.get('custody_location', '').strip()
        report.identifying_features = request.form.get('identifying_features', '').strip()
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                new_image = process_and_save_image(file, subfolder='reports')
                if new_image:
                    report.image_path = new_image
                    
        db.session.commit()
        
        if report.review_status == 'approved':
            evaluate_and_store_matches(report, is_lost=False)
            
        flash('Report updated successfully.', 'success')
        return redirect(url_for('reports.view_found', id=report.id))
        
    return render_template('reports/edit_report.html', report=report, report_type='found', categories=categories, locations=locations)

@reports_bp.route('/<string:report_type>/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_report(report_type, id):
    if report_type == 'lost':
        report = LostReport.query.get_or_404(id)
    else:
        report = FoundReport.query.get_or_404(id)
        
    if report.user_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    report.report_status = 'cancelled'
    audit = AuditLog(
        actor_id=current_user.id,
        action=f"{report_type}_report_cancelled",
        entity_type='report',
        entity_id=str(report.id),
        details=f"Report {report.report_code} cancelled by {current_user.full_name}."
    )
    db.session.add(audit)
    db.session.commit()
    
    flash(f'Report {report.report_code} has been cancelled.', 'info')
    return redirect(url_for('user.dashboard'))

