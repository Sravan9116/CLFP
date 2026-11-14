from app.extensions import db, socketio
from app.models.notification import Notification
from app.models.user import User

def create_notification(user_id, title, message, notification_type='info', link_url=None, related_report_id=None, related_claim_id=None):
    """
    Persists a notification in the database and broadcasts via Flask-SocketIO.
    """
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
        related_report_id=related_report_id,
        related_claim_id=related_claim_id,
        is_read=False
    )
    db.session.add(notif)
    db.session.commit()
    
    # Real-time WebSocket emission
    payload = notif.to_dict()
    try:
        room = f"user_{user_id}"
        socketio.emit('new_notification', payload, room=room)
    except Exception as e:
        # Fallback logging if socket emission encounters an issue
        pass
        
    return notif

def notify_admins(title, message, notification_type='admin_alert', link_url=None, related_report_id=None, related_claim_id=None):
    """
    Creates notifications for all administrators and broadcasts to admin_room.
    """
    admins = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
    created_notifs = []
    
    for admin in admins:
        notif = Notification(
            user_id=admin.id,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url,
            related_report_id=related_report_id,
            related_claim_id=related_claim_id,
            is_read=False
        )
        db.session.add(notif)
        created_notifs.append(notif)
        
    db.session.commit()
    
    try:
        if created_notifs:
            payload = created_notifs[0].to_dict()
            socketio.emit('admin_alert', payload, room='admin_room')
    except Exception:
        pass
        
    return created_notifs

def get_user_unread_count(user_id):
    """Returns unread notification count for user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

