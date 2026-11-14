from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User, Department
from app.models.notification import AuditLog
from app.services.email_service import (
    is_domain_allowed,
    send_verification_email,
    send_password_reset_email,
    verify_token
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
        
    departments = Department.query.filter_by(status='active').order_by(Department.department_name).all()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        institutional_id = request.form.get('institutional_id', '').strip()
        department_id = request.form.get('department_id')
        user_type = request.form.get('user_type', 'student')
        year_of_study = request.form.get('year_of_study')
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not full_name or not email or not institutional_id or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register.html', departments=departments)
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', departments=departments)
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/register.html', departments=departments)
            
        # Domain allowlist check
        if not is_domain_allowed(email):
            allowed = ", ".join(current_app.config.get('CAMPUS_EMAIL_DOMAINS', []))
            flash(f'Registration is restricted to authorized campus email domains ({allowed}).', 'danger')
            return render_template('auth/register.html', departments=departments)
            
        # Check uniqueness
        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))
            
        if User.query.filter_by(institutional_id=institutional_id).first():
            flash('An account with this Student/Staff ID already exists.', 'danger')
            return render_template('auth/register.html', departments=departments)
            
        # Create user
        user = User(
            full_name=full_name,
            email=email,
            institutional_id=institutional_id,
            department_id=int(department_id) if department_id else None,
            user_type=user_type,
            year_of_study=int(year_of_study) if (year_of_study and user_type == 'student') else None,
            phone=phone,
            role='user',  # Security: Users cannot self-assign admin roles
            account_status='active',
            email_verified=False
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Audit log
        audit = AuditLog(
            actor_id=user.id,
            action='user_registered',
            entity_type='user',
            entity_id=str(user.id),
            details=f"User {user.full_name} ({user.email}) registered with ID {user.institutional_id}."
        )
        db.session.add(audit)
        db.session.commit()
        
        # Send verification email (or console fallback in dev)
        send_verification_email(user)
        db.session.commit()
        
        flash('Account registered successfully! A verification email has been sent to your university address.', 'success')
        return render_template('auth/verify_notice.html', email=email, token=user.verification_token)
        
    return render_template('auth/register.html', departments=departments)

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    email = verify_token(token, salt='email-verification', max_age=86400)
    if not email:
        flash('The verification link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.login'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('auth.register'))
        
    user.email_verified = True
    user.verification_token = None
    
    audit = AuditLog(
        actor_id=user.id,
        action='email_verified',
        entity_type='user',
        entity_id=str(user.id),
        details=f"Email verified for {user.email}."
    )
    db.session.add(audit)
    db.session.commit()
    
    flash('Your university email address has been successfully verified! You may now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        remember = bool(request.form.get('remember_me'))
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email address or password.', 'danger')
            return render_template('auth/login.html')
            
        if user.account_status == 'suspended':
            flash('Your account has been suspended by campus administration. Please contact the help desk.', 'danger')
            return render_template('auth/login.html')
            
        # Note: If email not verified, we can either warn or allow in development
        if not user.email_verified and not current_app.config.get('TESTING'):
            # Allow automatic verify shortcut for ease of demo or prompt
            flash('Please verify your email address to access all features. You can resend verification if needed.', 'warning')
            
        login_user(user, remember=remember)
        
        # Audit log
        audit = AuditLog(
            actor_id=user.id,
            action='user_logged_in',
            entity_type='auth',
            entity_id=str(user.id),
            details=f"User {user.email} logged in successfully."
        )
        db.session.add(audit)
        db.session.commit()
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
            
        if user.is_admin:
            flash(f'Welcome back, Administrator {user.full_name}!', 'info')
            return redirect(url_for('admin.dashboard'))
            
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect(url_for('user.dashboard'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    audit = AuditLog(
        actor_id=current_user.id,
        action='user_logged_out',
        entity_type='auth',
        entity_id=str(current_user.id),
        details=f"User {current_user.email} logged out."
    )
    db.session.add(audit)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_password_reset_email(user)
            db.session.commit()
            
        flash('If that university email is registered, password reset instructions have been sent.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_token(token, salt='password-reset', max_age=3600)  # 1 hour
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User account not found.', 'danger')
        return redirect(url_for('auth.register'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html')
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/reset_password.html')
            
        user.set_password(password)
        user.reset_token = None
        
        audit = AuditLog(
            actor_id=user.id,
            action='password_reset_completed',
            entity_type='auth',
            entity_id=str(user.id),
            details=f"Password reset completed for {user.email}."
        )
        db.session.add(audit)
        db.session.commit()
        
        flash('Your password has been reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html')

