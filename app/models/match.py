from datetime import datetime
from app.extensions import db

class ItemMatch(db.Model):
    __tablename__ = 'item_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey('lost_reports.id', ondelete='CASCADE'), nullable=False)
    found_report_id = db.Column(db.Integer, db.ForeignKey('found_reports.id', ondelete='CASCADE'), nullable=False)
    match_score = db.Column(db.Float, nullable=False)  # 0 to 100
    match_explanation = db.Column(db.Text, nullable=True)
    algorithm_version = db.Column(db.String(20), default='v1.0')
    match_status = db.Column(db.String(30), default='potential')  # 'potential', 'claimed', 'dismissed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('lost_report_id', 'found_report_id', name='uq_lost_found_match'),
    )
    
    @property
    def classification(self):
        if self.match_score >= 85:
            return 'Strong Match'
        elif self.match_score >= 65:
            return 'Possible Match'
        elif self.match_score >= 40:
            return 'Weak Match'
        return 'Low Relevance'
        
    @property
    def badge_class(self):
        if self.match_score >= 85:
            return 'bg-success'
        elif self.match_score >= 65:
            return 'bg-primary'
        elif self.match_score >= 40:
            return 'bg-warning text-dark'
        return 'bg-secondary'
        
    def to_dict(self):
        return {
            'id': self.id,
            'lost_report_id': self.lost_report_id,
            'found_report_id': self.found_report_id,
            'match_score': round(self.match_score, 1),
            'classification': self.classification,
            'match_explanation': self.match_explanation,
            'algorithm_version': self.algorithm_version,
            'match_status': self.match_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'lost_report': self.lost_report.to_dict() if self.lost_report else None,
            'found_report': self.found_report.to_dict() if self.found_report else None
        }

