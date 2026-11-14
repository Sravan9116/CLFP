from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models.user import User, Department
from app.models.report import LostReport, FoundReport, ItemCategory, CampusLocation
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.match import ItemMatch
from app.models.notification import Announcement, AuditLog, SystemSetting
from app.services.matching_service import evaluate_and_store_matches, recalculate_all_matches
from app.services.claim_service import review_claim
from app.services.handover_service import schedule_handover, complete_handover
from app.services.notification_service import create_notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)

@admin_bp.route('')
@admin_bp.route('/dashboard')
def dashboard():
    # Real database statistics
    total_users = User.query.count()
    total_lost = LostReport.query.count()
    total_found = FoundReport.query.count()
    pending_approvals = (
        LostReport.query.filter_by(review_status='pending_review').count() +
        FoundReport.query.filter_by(review_status='pending_review').count()
    )
    active_claims = Claim.query.filter(Claim.claim_status.in_(['submitted', 'under_review', 'evidence_required', 'approved', 'handover_scheduled'])).count()
    successful_recoveries = Handover.query.filter_by(handover_status='completed').count()
    rejected_reports = (
        LostReport.query.filter_by(review_status='rejected').count() +
        FoundReport.query.filter_by(review_status='rejected').count()
    )

    # Recovery rate percentage
    recovery_rate = round((successful_recoveries / max(total_lost + total_found, 1)) * 100, 1)

    # Category breakdown for Chart.js
    categories = ItemCategory.query.filter_by(status='active').all()
    cat_labels = [c.category_name for c in categories]
    cat_lost_counts = [LostReport.query.filter_by(category_id=c.id).count() for c in categories]
    cat_found_counts = [FoundReport.query.filter_by(category_id=c.id).count() for c in categories]

    # Locations data for Chart.js
    top_locations = db.session.query(
        CampusLocation.location_name,
        func.count(LostReport.id) + func.count(FoundReport.id)
    ).outerjoin(LostReport, CampusLocation.id == LostReport.location_id)\
     .outerjoin(FoundReport, CampusLocation.id == FoundReport.location_id)\
     .group_by(CampusLocation.id)\
     .order_by((func.count(LostReport.id) + func.count(FoundReport.id)).desc())\
     .limit(6).all()

    # Claims status distribution
    claim_statuses = ['submitted', 'under_review', 'evidence_required', 'approved', 'handover_scheduled', 'returned', 'rejected']
    claim_counts = [Claim.query.filter_by(claim_status=s).count() for s in claim_statuses]

    # Recent items needing review
    pending_lost = LostReport.query.filter_by(review_status='pending_review').order_by(LostReport.created_at.desc()).limit(5).all()
    pending_found = FoundReport.query.filter_by(review_status='pending_review').order_by(FoundReport.created_at.desc()).limit(5).all()
    recent_claims = Claim.query.order_by(Claim.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_lost=total_lost,
        total_found=total_found,
        pending_approvals=pending_approvals,
        active_claims=active_claims,
        successful_recoveries=successful_recoveries,
        rejected_reports=rejected_reports,
        recovery_rate=recovery_rate,
        cat_labels=cat_labels,
        cat_lost_counts=cat_lost_counts,
        cat_found_counts=cat_found_counts,
        top_locations=[(loc[0], loc[1] or 0) for loc in top_locations],
        claim_statuses=claim_statuses,
        claim_counts=claim_counts,
        pending_lost=pending_lost,
        pending_found=pending_found,
        recent_claims=recent_claims
    )

@admin_bp.route('/reports')
def reports():
    rtype = request.args.get('type', 'all')  # 'all', 'lost', 'found'
    status = request.args.get('status', 'all')  # 'all', 'pending_review', 'approved', 'rejected'
    q = request.args.get('q', '').strip()

    lost_query = LostReport.query
    found_query = FoundReport.query

    if status != 'all':
        lost_query = lost_query.filter_by(review_status=status)
        found_query = found_query.filter_by(review_status=status)

    if q:
        lost_query = lost_query.filter(LostReport.item_name.ilike(f'%{q}%') | LostReport.report_code.ilike(f'%{q}%'))
        found_query = found_query.filter(FoundReport.item_name.ilike(f'%{q}%') | FoundReport.report_code.ilike(f'%{q}%'))

    lost_reports = lost_query.order_by(LostReport.created_at.desc()).all() if rtype in ['all', 'lost'] else []
    found_reports = found_query.order_by(FoundReport.created_at.desc()).all() if rtype in ['all', 'found'] else []

    return render_template(
        'admin/reports.html',
        lost_reports=lost_reports,
        found_reports=found_reports,
        rtype=rtype,
        status=status,
        q=q
    )

@admin_bp.route('/reports/<string:rtype>/<int:id>/approve', methods=['POST'])
def approve_report(rtype, id):
    if rtype == 'lost':
        report = LostReport.query.get_or_404(id)
        report.review_status = 'approved'
        report.rejection_reason = None
        db.session.commit()
        # Trigger matching engine
        evaluate_and_store_matches(report, is_lost=True)
        # Notify user
        create_notification(
            user_id=report.user_id,
            title="Lost Report Approved",
            message=f"Your report {report.report_code} ('{report.item_name}') has been approved and is now active in public discovery.",
            notification_type='report_status',
            link_url=f"/reports/lost/{report.id}",
            related_report_id=report.id
        )
    else:
        report = FoundReport.query.get_or_404(id)
        report.review_status = 'approved'
        report.rejection_reason = None
        db.session.commit()
        evaluate_and_store_matches(report, is_lost=False)
        create_notification(
            user_id=report.user_id,
            title="Found Report Approved",
            message=f"Your found report {report.report_code} ('{report.item_name}') has been verified and published.",
            notification_type='report_status',
            link_url=f"/reports/found/{report.id}",
            related_report_id=report.id
        )

    audit = AuditLog(
        actor_id=current_user.id,
        action=f"{rtype}_report_approved",
        entity_type='report',
        entity_id=str(report.id),
        details=f"Admin {current_user.full_name} approved report {report.report_code}."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Report {report.report_code} approved successfully and intelligent matching triggered.", "success")
    return redirect(request.referrer or url_for('admin.reports'))

@admin_bp.route('/reports/<string:rtype>/<int:id>/reject', methods=['POST'])
def reject_report(rtype, id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash("A rejection reason is required.", "danger")
        return redirect(request.referrer or url_for('admin.reports'))

    if rtype == 'lost':
        report = LostReport.query.get_or_404(id)
    else:
        report = FoundReport.query.get_or_404(id)

    report.review_status = 'rejected'
    report.rejection_reason = reason
    
    audit = AuditLog(
        actor_id=current_user.id,
        action=f"{rtype}_report_rejected",
        entity_type='report',
        entity_id=str(report.id),
        details=f"Admin {current_user.full_name} rejected report {report.report_code}. Reason: {reason}"
    )
    db.session.add(audit)
    db.session.commit()

    create_notification(
        user_id=report.user_id,
        title=f"Report {report.report_code} Rejected",
        message=f"Your report was not approved. Reason: {reason}",
        notification_type='report_status',
        link_url=f"/reports/{rtype}/{report.id}",
        related_report_id=report.id
    )

    flash(f"Report {report.report_code} rejected.", "info")
    return redirect(request.referrer or url_for('admin.reports'))

@admin_bp.route('/claims')
def claims():
    status = request.args.get('status', 'all')
    query = Claim.query
    if status != 'all':
        query = query.filter_by(claim_status=status)
    all_claims = query.order_by(Claim.created_at.desc()).all()
    locations = CampusLocation.query.filter_by(status='active').all()
    return render_template('admin/claims.html', claims=all_claims, status=status, locations=locations)

@admin_bp.route('/claims/<int:id>')
def view_claim(id):
    claim = Claim.query.get_or_404(id)
    locations = CampusLocation.query.filter_by(status='active').all()
    return render_template('admin/claim_detail.html', claim=claim, locations=locations)

@admin_bp.route('/claims/<int:id>/review', methods=['POST'])
def process_claim_review(id):
    new_status = request.form.get('status')
    review_notes = request.form.get('review_notes', '').strip()
    rejection_reason = request.form.get('rejection_reason', '').strip()

    success, error = review_claim(id, current_user, new_status, review_notes, rejection_reason)
    if not success:
        flash(error, 'danger')
    else:
        flash(f'Claim updated to {new_status.replace("_", " ").title()}.', 'success')
    return redirect(url_for('admin.view_claim', id=id))

@admin_bp.route('/claims/<int:id>/schedule-handover', methods=['POST'])
def schedule_claim_handover(id):
    location_id = request.form.get('location_id')
    scheduled_date_str = request.form.get('scheduled_date')
    scheduled_time_str = request.form.get('scheduled_time')
    notes = request.form.get('notes', '').strip()

    if not location_id or not scheduled_date_str or not scheduled_time_str:
        flash('Please provide location, date, and time for the handover.', 'danger')
        return redirect(url_for('admin.view_claim', id=id))

    try:
        scheduled_at = datetime.strptime(f"{scheduled_date_str} {scheduled_time_str}", '%Y-%m-%d %H:%M')
    except ValueError:
        flash('Invalid date or time format.', 'danger')
        return redirect(url_for('admin.view_claim', id=id))

    handover, error = schedule_handover(id, int(location_id), scheduled_at, current_user, notes)
    if error:
        flash(error, 'danger')
    else:
        flash(f"Handover {handover.recovery_code} successfully scheduled and QR code generated.", 'success')
    return redirect(url_for('admin.view_claim', id=id))

@admin_bp.route('/handovers/<int:id>/complete', methods=['POST'])
def finish_handover(id):
    success, error = complete_handover(id, current_user)
    if not success:
        flash(error, 'danger')
    else:
        flash("Item verified and marked as RETURNED! Official recovery record logged.", 'success')
    return redirect(request.referrer or url_for('admin.claims'))

@admin_bp.route('/matches')
def matches():
    all_matches = ItemMatch.query.order_by(ItemMatch.match_score.desc()).all()
    return render_template('admin/matches.html', matches=all_matches)

@admin_bp.route('/matches/recalculate', methods=['POST'])
def trigger_matching():
    count = recalculate_all_matches()
    flash(f"Intelligent item matching completed. Evaluated and identified {count} compatible items.", 'success')
    return redirect(url_for('admin.matches'))

@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    departments = Department.query.all()
    return render_template('admin/users.html', users=all_users, departments=departments)

@admin_bp.route('/users/<int:id>/role', methods=['POST'])
def update_user_role(id):
    if not current_user.is_super_admin:
        flash('Only Super Administrators can modify user roles.', 'danger')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(id)
    new_role = request.form.get('role')
    if new_role in ['user', 'admin', 'super_admin']:
        user.role = new_role
        audit = AuditLog(
            actor_id=current_user.id,
            action='user_role_changed',
            entity_type='user',
            entity_id=str(user.id),
            details=f"Super Admin {current_user.full_name} changed {user.email} role to {new_role}."
        )
        db.session.add(audit)
        db.session.commit()
        flash(f"Role updated to {new_role} for {user.full_name}.", 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:id>/status', methods=['POST'])
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot suspend your own account.', 'danger')
        return redirect(url_for('admin.users'))

    user.account_status = 'suspended' if user.account_status == 'active' else 'active'
    audit = AuditLog(
        actor_id=current_user.id,
        action='user_status_toggled',
        entity_type='user',
        entity_id=str(user.id),
        details=f"Admin {current_user.full_name} updated {user.email} status to {user.account_status}."
    )
    db.session.add(audit)
    db.session.commit()
    flash(f"User account status updated to {user.account_status}.", 'info')
    return redirect(url_for('admin.users'))

@admin_bp.route('/locations', methods=['GET', 'POST'])
def locations():
    if request.method == 'POST':
        loc_name = request.form.get('location_name', '').strip()
        category = request.form.get('location_category', 'General')
        desc = request.form.get('description', '').strip()
        lat_str = request.form.get('latitude')
        lng_str = request.form.get('longitude')

        if not loc_name:
            flash('Location name is required.', 'danger')
        else:
            loc = CampusLocation(
                location_name=loc_name,
                location_category=category,
                description=desc,
                latitude=float(lat_str) if lat_str else None,
                longitude=float(lng_str) if lng_str else None,
                status='active'
            )
            db.session.add(loc)
            db.session.commit()
            flash(f"Campus location '{loc_name}' created.", 'success')

    all_locations = CampusLocation.query.order_by(CampusLocation.location_name).all()
    return render_template('admin/locations.html', locations=all_locations)

@admin_bp.route('/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'POST':
        cat_name = request.form.get('category_name', '').strip()
        icon_class = request.form.get('icon_class', 'bi-tag')
        desc = request.form.get('description', '').strip()

        if not cat_name:
            flash('Category name is required.', 'danger')
        else:
            cat = ItemCategory(
                category_name=cat_name,
                icon_class=icon_class,
                description=desc,
                status='active'
            )
            db.session.add(cat)
            db.session.commit()
            flash(f"Category '{cat_name}' added.", 'success')

    all_cats = ItemCategory.query.order_by(ItemCategory.category_name).all()
    return render_template('admin/categories.html', categories=all_cats)

@admin_bp.route('/announcements', methods=['GET', 'POST'])
def announcements():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'General')
        target_audience = request.form.get('target_audience', 'all')
        expires_at_str = request.form.get('expires_at')

        if not title or not description:
            flash('Title and description are required.', 'danger')
        else:
            ann = Announcement(
                title=title,
                description=description,
                category=category,
                target_audience=target_audience,
                expires_at=datetime.strptime(expires_at_str, '%Y-%m-%d').date() if expires_at_str else None,
                created_by=current_user.id,
                status='active'
            )
            db.session.add(ann)
            db.session.commit()
            flash('Announcement published to campus.', 'success')

    all_announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=all_announcements)

@admin_bp.route('/audit-logs')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(150).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        domains = request.form.get('email_domains', '').strip()
        if domains:
            setting = SystemSetting.query.filter_by(key='CAMPUS_EMAIL_DOMAINS').first()
            if not setting:
                setting = SystemSetting(key='CAMPUS_EMAIL_DOMAINS', value=domains, description="Allowed email domains for registration")
                db.session.add(setting)
            else:
                setting.value = domains
            db.session.commit()
            flash('System settings saved.', 'success')
            
    domains_setting = SystemSetting.query.filter_by(key='CAMPUS_EMAIL_DOMAINS').first()
    domains_val = domains_setting.value if domains_setting else ", ".join(current_app.config.get('CAMPUS_EMAIL_DOMAINS', []))
    return render_template('admin/settings.html', domains=domains_val)

