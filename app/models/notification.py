from datetime import datetime
from app.extensions import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info', nullable=False)
    # Types: 'report_approved', 'report_rejected', 'match_found', 'claim_submitted', 'claim_status', 'evidence_required', 'handover_scheduled', 'handover_confirmed', 'message', 'announcement', 'admin_alert'
    link_url = db.Column(db.String(255), nullable=True)
    related_report_id = db.Column(db.Integer, nullable=True)
    related_claim_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'link_url': self.link_url,
            'related_report_id': self.related_report_id,
            'related_claim_id': self.related_claim_id,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'created_at_iso': self.created_at.isoformat() if self.created_at else None
        }

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='General', nullable=False)
    target_audience = db.Column(db.String(50), default='all', nullable=False)  # 'all', 'students', 'faculty', 'staff'
    expires_at = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)  # 'active', 'inactive'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', foreign_keys=[created_by], backref='announcements')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'target_audience': self.target_audience,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'author_name': self.author.full_name if self.author else 'Admin',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # e.g. 'report_approved', 'claim_rejected'
    entity_type = db.Column(db.String(50), nullable=False)  # 'report', 'claim', 'user', 'location', 'category', 'handover', 'auth'
    entity_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'actor_name': self.actor.full_name if self.actor else 'System',
            'actor_role': self.actor.role if self.actor else 'system',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

