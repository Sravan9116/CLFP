from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='active')
    
    users = db.relationship('User', backref='department', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'department_name': self.department_name,
            'department_code': self.department_code,
            'status': self.status
        }

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    institutional_id = db.Column(db.String(50), unique=True, index=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'user', 'admin', 'super_admin'
    user_type = db.Column(db.String(20), default='student')  # 'student', 'faculty', 'staff'
    year_of_study = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    account_status = db.Column(db.String(20), default='active')  # 'active', 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lost_reports = db.relationship('LostReport', backref='reporter', foreign_keys='LostReport.user_id', lazy='dynamic')
    found_reports = db.relationship('FoundReport', backref='finder', foreign_keys='FoundReport.user_id', lazy='dynamic')
    claims = db.relationship('Claim', backref='claimant', foreign_keys='Claim.claimant_id', lazy='dynamic')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def is_admin(self):
        return self.role in ['admin', 'super_admin']
        
    @property
    def is_super_admin(self):
        return self.role == 'super_admin'
        
    @property
    def is_active(self):
        return self.account_status == 'active'
        
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'institutional_id': self.institutional_id,
            'department': self.department.department_name if self.department else None,
            'role': self.role,
            'user_type': self.user_type,
            'year_of_study': self.year_of_study,
            'phone': self.phone,
            'email_verified': self.email_verified,
            'account_status': self.account_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

