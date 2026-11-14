from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notification import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('')
@login_required
def index():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('user/notifications.html', notifications=notifications)

@notifications_bp.route('/<int:id>/read', methods=['POST'])
@login_required
def mark_read(id):
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'id': notif.id})
    return redirect(notif.link_url or url_for('notifications.index'))

@notifications_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('notifications.index'))

