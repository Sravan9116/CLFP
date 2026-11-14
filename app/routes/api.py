from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required, login_user
from app.extensions import db, csrf
from app.models.user import User
from app.models.report import LostReport, FoundReport, CampusLocation, ItemCategory
from app.models.claim import Claim
from app.models.match import ItemMatch
from app.models.notification import Notification
from app.services.matching_service import recalculate_all_matches

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Exempt JSON API routes from CSRF if using API calls with token/session
@api_bp.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'app': 'CampusConnect Lost & Found Portal',
        'version': '2.0.0'
    })

@api_bp.route('/locations')
def get_locations():
    locations = CampusLocation.query.filter_by(status='active').all()
    features = []
    for loc in locations:
        if loc.latitude and loc.longitude:
            lost_count = LostReport.query.filter_by(location_id=loc.id, review_status='approved').count()
            found_count = FoundReport.query.filter_by(location_id=loc.id, review_status='approved').count()
            features.append({
                'id': loc.id,
                'name': loc.location_name,
                'category': loc.location_category,
                'description': loc.description,
                'lat': loc.latitude,
                'lng': loc.longitude,
                'lost_count': lost_count,
                'found_count': found_count
            })
    return jsonify({'locations': features})

@api_bp.route('/reports')
def get_reports():
    rtype = request.args.get('type', 'all')
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    
    results = []
    if rtype in ['all', 'lost']:
        lost_q = LostReport.query.filter_by(review_status='approved', report_status='active')
        if q:
            lost_q = lost_q.filter(LostReport.item_name.ilike(f'%{q}%'))
        if category_id:
            lost_q = lost_q.filter_by(category_id=category_id)
        for r in lost_q.order_by(LostReport.created_at.desc()).limit(30).all():
            results.append(r.to_dict())
            
    if rtype in ['all', 'found']:
        found_q = FoundReport.query.filter_by(review_status='approved', report_status='active')
        if q:
            found_q = found_q.filter(FoundReport.item_name.ilike(f'%{q}%'))
        if category_id:
            found_q = found_q.filter_by(category_id=category_id)
        for r in found_q.order_by(FoundReport.created_at.desc()).limit(30).all():
            results.append(r.to_dict())
            
    return jsonify({'reports': results, 'count': len(results)})

@api_bp.route('/reports/<int:id>')
def get_report_detail(id):
    rtype = request.args.get('type', 'lost')
    if rtype == 'lost':
        report = LostReport.query.get_or_404(id)
    else:
        report = FoundReport.query.get_or_404(id)
        
    include_sensitive = current_user.is_authenticated and (current_user.id == report.user_id or current_user.is_admin)
    return jsonify({'report': report.to_dict(include_sensitive=include_sensitive)})

@api_bp.route('/notifications/poll')
@login_required
def poll_notifications():
    """
    Polling fallback for real-time notifications in case WebSockets are interrupted.
    """
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        'unread_count': count,
        'notifications': [n.to_dict() for n in unread]
    })

@api_bp.route('/notifications/<int:id>/read', methods=['PUT', 'POST'])
@login_required
def read_notification(id):
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'id': notif.id})

@api_bp.route('/notifications/read-all', methods=['PUT', 'POST'])
@login_required
def read_all_notifications():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/matches')
@login_required
def get_matches():
    if current_user.is_admin:
        matches = ItemMatch.query.order_by(ItemMatch.match_score.desc()).limit(50).all()
    else:
        user_lost_ids = [r.id for r in current_user.lost_reports.all()]
        matches = ItemMatch.query.filter(ItemMatch.lost_report_id.in_(user_lost_ids)).order_by(ItemMatch.match_score.desc()).all()
    return jsonify({'matches': [m.to_dict() for m in matches]})

@api_bp.route('/matches/recalculate', methods=['POST'])
@login_required
def recalculate_matches():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    count = recalculate_all_matches()
    return jsonify({'success': True, 'matches_processed': count})

