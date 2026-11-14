from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.report import LostReport, FoundReport
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.match import ItemMatch
from app.models.notification import Notification
from app.models.message import Conversation

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    my_lost_reports = LostReport.query.filter_by(user_id=current_user.id).order_by(LostReport.created_at.desc()).all()
    my_found_reports = FoundReport.query.filter_by(user_id=current_user.id).order_by(FoundReport.created_at.desc()).all()
    my_claims = Claim.query.filter_by(claimant_id=current_user.id).order_by(Claim.created_at.desc()).all()
    
    # Recovered count: claims marked 'returned' or lost reports 'resolved'
    recovered_count = Claim.query.filter_by(claimant_id=current_user.id, claim_status='returned').count()
    
    # Matches for user's active lost reports
    lost_ids = [r.id for r in my_lost_reports if r.report_status == 'active']
    potential_matches = []
    if lost_ids:
        potential_matches = ItemMatch.query.filter(
            ItemMatch.lost_report_id.in_(lost_ids),
            ItemMatch.match_score >= 40.0
        ).order_by(ItemMatch.match_score.desc()).limit(10).all()
        
    recent_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    conversations = Conversation.query.join(Claim).filter(Claim.claimant_id == current_user.id).order_by(Conversation.updated_at.desc()).limit(5).all()

    return render_template(
        'user/dashboard.html',
        lost_reports=my_lost_reports,
        found_reports=my_found_reports,
        claims=my_claims,
        recovered_count=recovered_count,
        potential_matches=potential_matches,
        notifications=recent_notifications,
        conversations=conversations
    )

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        current_user.phone = phone
        
        if new_password:
            if not current_password or not current_user.check_password(current_password):
                flash('Current password verification failed.', 'danger')
                return render_template('user/profile.html')
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return render_template('user/profile.html')
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long.', 'danger')
                return render_template('user/profile.html')
            current_user.set_password(new_password)
            flash('Password updated successfully.', 'success')
            
        db.session.commit()
        flash('Profile settings saved.', 'success')
        return redirect(url_for('user.profile'))
        
    return render_template('user/profile.html')

