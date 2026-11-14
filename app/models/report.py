from datetime import datetime
from app.extensions import db

class CampusLocation(db.Model):
    __tablename__ = 'campus_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), unique=True, nullable=False)
    location_category = db.Column(db.String(50), nullable=False) # 'Library', 'Main Block', etc.
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='active')
    
    lost_reports = db.relationship('LostReport', backref='location', lazy='dynamic')
    found_reports = db.relationship('FoundReport', backref='location', lazy='dynamic')
    handovers = db.relationship('Handover', backref='location', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'location_name': self.location_name,
            'location_category': self.location_category,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status
        }

class ItemCategory(db.Model):
    __tablename__ = 'item_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), unique=True, nullable=False)
    icon_class = db.Column(db.String(50), default='bi-tag')
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    
    lost_reports = db.relationship('LostReport', backref='category', lazy='dynamic')
    found_reports = db.relationship('FoundReport', backref='category', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_name': self.category_name,
            'icon_class': self.icon_class,
            'description': self.description,
            'status': self.status
        }

class LostReport(db.Model):
    __tablename__ = 'lost_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_code = db.Column(db.String(30), unique=True, index=True, nullable=False)  # LOST-2026-00001
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('item_categories.id'), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(80), nullable=True)
    primary_color = db.Column(db.String(40), nullable=False)
    secondary_color = db.Column(db.String(40), nullable=True)
    date_lost = db.Column(db.Date, nullable=False)
    approximate_time = db.Column(db.String(40), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('campus_locations.id'), nullable=False)
    additional_location = db.Column(db.String(255), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    identifying_features = db.Column(db.Text, nullable=True)  # Sensitive details
    contact_preference = db.Column(db.String(50), default='email')
    
    # Review status by administrator
    review_status = db.Column(db.String(30), default='pending_review', nullable=False)  # 'pending_review', 'approved', 'rejected', 'flagged'
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Overall operational status
    report_status = db.Column(db.String(30), default='active', nullable=False)  # 'active', 'resolved', 'closed', 'cancelled'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Matches and claims
    matches = db.relationship('ItemMatch', backref='lost_report', cascade='all, delete-orphan', lazy='dynamic')
    claims = db.relationship('Claim', backref='lost_report', lazy='dynamic')
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'report_type': 'lost',
            'report_code': self.report_code,
            'item_name': self.item_name,
            'category': self.category.category_name if self.category else None,
            'category_id': self.category_id,
            'description': self.description,
            'brand': self.brand,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'date_lost': self.date_lost.isoformat() if self.date_lost else None,
            'approximate_time': self.approximate_time,
            'location': self.location.location_name if self.location else None,
            'location_id': self.location_id,
            'additional_location': self.additional_location,
            'image_path': self.image_path,
            'review_status': self.review_status,
            'report_status': self.report_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reporter_code': f"USER-{self.user_id:04d}"
        }
        if include_sensitive:
            data['identifying_features'] = self.identifying_features
            data['contact_preference'] = self.contact_preference
            data['rejection_reason'] = self.rejection_reason
            data['reporter_name'] = self.reporter.full_name if self.reporter else None
            data['reporter_email'] = self.reporter.email if self.reporter else None
        return data

class FoundReport(db.Model):
    __tablename__ = 'found_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_code = db.Column(db.String(30), unique=True, index=True, nullable=False)  # FOUND-2026-00001
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('item_categories.id'), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(80), nullable=True)
    primary_color = db.Column(db.String(40), nullable=False)
    secondary_color = db.Column(db.String(40), nullable=True)
    date_found = db.Column(db.Date, nullable=False)
    approximate_time = db.Column(db.String(40), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('campus_locations.id'), nullable=False)
    
    # Custody
    custody_status = db.Column(db.String(50), default='finder_possession', nullable=False)  # 'finder_possession', 'security_office', 'admin_office', 'collection_point'
    custody_location = db.Column(db.String(255), nullable=True)
    
    image_path = db.Column(db.String(255), nullable=True)
    identifying_features = db.Column(db.Text, nullable=True)  # Sensitive characteristics kept confidential to prevent fraud
    
    review_status = db.Column(db.String(30), default='pending_review', nullable=False)  # 'pending_review', 'approved', 'rejected', 'flagged'
    rejection_reason = db.Column(db.Text, nullable=True)
    
    report_status = db.Column(db.String(30), default='active', nullable=False)  # 'active', 'claimed', 'returned', 'closed'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Matches and claims
    matches = db.relationship('ItemMatch', backref='found_report', cascade='all, delete-orphan', lazy='dynamic')
    claims = db.relationship('Claim', backref='found_report', cascade='all, delete-orphan', lazy='dynamic')
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'report_type': 'found',
            'report_code': self.report_code,
            'item_name': self.item_name,
            'category': self.category.category_name if self.category else None,
            'category_id': self.category_id,
            'description': self.description,
            'brand': self.brand,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'date_found': self.date_found.isoformat() if self.date_found else None,
            'approximate_time': self.approximate_time,
            'location': self.location.location_name if self.location else None,
            'location_id': self.location_id,
            'custody_status': self.custody_status,
            'custody_location': self.custody_location,
            'image_path': self.image_path,
            'review_status': self.review_status,
            'report_status': self.report_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'finder_code': f"USER-{self.user_id:04d}"
        }
        if include_sensitive:
            data['identifying_features'] = self.identifying_features
            data['rejection_reason'] = self.rejection_reason
            data['finder_name'] = self.finder.full_name if self.finder else None
            data['finder_email'] = self.finder.email if self.finder else None
        return data

class ReportImage(db.Model):
    __tablename__ = 'report_images'
    
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(10), nullable=False)  # 'lost' or 'found'
    report_id = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

