from datetime import datetime
from app.extensions import db

class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_code = db.Column(db.String(30), unique=True, index=True, nullable=False)  # CLAIM-2026-00001
    lost_report_id = db.Column(db.Integer, db.ForeignKey('lost_reports.id'), nullable=True)
    found_report_id = db.Column(db.Integer, db.ForeignKey('found_reports.id'), nullable=False)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ownership verification answers (kept confidential)
    ownership_description = db.Column(db.Text, nullable=False)
    identifying_answers = db.Column(db.Text, nullable=True)
    approximate_purchase_date = db.Column(db.String(50), nullable=True)
    evidence_path = db.Column(db.String(255), nullable=True)  # File path to receipt/proof
    contact_method = db.Column(db.String(50), default='email')
    
    # Workflow status
    claim_status = db.Column(db.String(40), default='submitted', nullable=False)
    # Statuses: 'submitted', 'under_review', 'evidence_required', 'approved', 'rejected', 'handover_scheduled', 'returned', 'cancelled'
    
    review_notes = db.Column(db.Text, nullable=True)  # Admin internal notes
    rejection_reason = db.Column(db.Text, nullable=True)  # Admin feedback for rejection
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_claims')
    handover = db.relationship('Handover', backref='claim', uselist=False, cascade='all, delete-orphan')
    conversation = db.relationship('Conversation', backref='claim', uselist=False, cascade='all, delete-orphan')

    @property
    def status_badge_class(self):
        badges = {
            'submitted': 'bg-secondary',
            'under_review': 'bg-info text-dark',
            'evidence_required': 'bg-warning text-dark',
            'approved': 'bg-primary',
            'handover_scheduled': 'bg-primary text-white',
            'returned': 'bg-success',
            'rejected': 'bg-danger',
            'cancelled': 'bg-secondary'
        }
        return badges.get(self.claim_status, 'bg-secondary')

    def to_dict(self, include_confidential=False):
        data = {
            'id': self.id,
            'claim_code': self.claim_code,
            'lost_report_id': self.lost_report_id,
            'found_report_id': self.found_report_id,
            'claimant_id': self.claimant_id,
            'claim_status': self.claim_status,
            'status_badge_class': self.status_badge_class,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'has_handover': bool(self.handover),
            'handover_status': self.handover.handover_status if self.handover else None,
            'found_item_name': self.found_report.item_name if self.found_report else None,
            'found_report_code': self.found_report.report_code if self.found_report else None
        }
        if include_confidential:
            data['ownership_description'] = self.ownership_description
            data['identifying_answers'] = self.identifying_answers
            data['approximate_purchase_date'] = self.approximate_purchase_date
            data['evidence_path'] = self.evidence_path
            data['review_notes'] = self.review_notes
            data['rejection_reason'] = self.rejection_reason
            data['claimant_name'] = self.claimant.full_name if self.claimant else None
            data['claimant_email'] = self.claimant.email if self.claimant else None
            data['claimant_institutional_id'] = self.claimant.institutional_id if self.claimant else None
            data['reviewer_name'] = self.reviewer.full_name if self.reviewer else None
        return data

