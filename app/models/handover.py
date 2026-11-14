from datetime import datetime
from app.extensions import db

class Handover(db.Model):
    __tablename__ = 'handovers'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id', ondelete='CASCADE'), nullable=False, unique=True)
    recovery_code = db.Column(db.String(40), unique=True, index=True, nullable=False)  # REC-2026-00001
    scheduled_location_id = db.Column(db.Integer, db.ForeignKey('campus_locations.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    
    # Dual confirmation
    claimant_confirmed = db.Column(db.Boolean, default=False)
    administrator_confirmed = db.Column(db.Boolean, default=False)
    verified_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    handover_status = db.Column(db.String(30), default='scheduled', nullable=False)
    # 'scheduled', 'confirmed_by_claimant', 'completed', 'cancelled'
    
    notes = db.Column(db.Text, nullable=True)
    qr_code_path = db.Column(db.String(255), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    verified_by_admin = db.relationship('User', foreign_keys=[verified_by_admin_id], backref='verified_handovers')

    @property
    def status_badge_class(self):
        badges = {
            'scheduled': 'bg-primary',
            'confirmed_by_claimant': 'bg-info text-dark',
            'completed': 'bg-success',
            'cancelled': 'bg-danger'
        }
        return badges.get(self.handover_status, 'bg-secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'claim_id': self.claim_id,
            'recovery_code': self.recovery_code,
            'location_name': self.location.location_name if self.location else None,
            'location_id': self.scheduled_location_id,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'claimant_confirmed': self.claimant_confirmed,
            'administrator_confirmed': self.administrator_confirmed,
            'handover_status': self.handover_status,
            'notes': self.notes,
            'qr_code_path': self.qr_code_path,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'verified_by': self.verified_by_admin.full_name if self.verified_by_admin else None,
            'status_badge_class': self.status_badge_class
        }

