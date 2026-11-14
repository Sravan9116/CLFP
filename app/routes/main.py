from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models.report import LostReport, FoundReport, ItemCategory, CampusLocation
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.notification import Announcement

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Database-backed live platform statistics
    total_lost = LostReport.query.count()
    total_found = FoundReport.query.count()
    total_returned = Handover.query.filter_by(handover_status='completed').count()
    active_reports = (
        LostReport.query.filter_by(report_status='active', review_status='approved').count() +
        FoundReport.query.filter_by(report_status='active', review_status='approved').count()
    )
    
    # Recent approved reports (max 8)
    recent_lost = LostReport.query.filter_by(
        review_status='approved',
        report_status='active'
    ).order_by(LostReport.created_at.desc()).limit(4).all()
    
    recent_found = FoundReport.query.filter_by(
        review_status='approved',
        report_status='active'
    ).order_by(FoundReport.created_at.desc()).limit(4).all()
    
    # Active announcements
    announcements = Announcement.query.filter_by(status='active').order_by(Announcement.created_at.desc()).limit(3).all()
    
    # Categories for quick filter badges
    categories = ItemCategory.query.filter_by(status='active').all()
    
    return render_template(
        'index.html',
        total_lost=total_lost,
        total_found=total_found,
        total_returned=total_returned,
        active_reports=active_reports,
        recent_lost=recent_lost,
        recent_found=recent_found,
        announcements=announcements,
        categories=categories
    )

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@main_bp.route('/about')
def about():
    locations_count = CampusLocation.query.filter_by(status='active').count()
    categories_count = ItemCategory.query.filter_by(status='active').count()
    return render_template('about.html', locations_count=locations_count, categories_count=categories_count)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        flash('Thank you for contacting the Campus Lost & Found Administrative Center. We will respond promptly.', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

