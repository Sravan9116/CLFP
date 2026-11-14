import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
from flask import current_app, url_for
from flask_mail import Message
from app.extensions import mail

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def generate_token(email, salt='email-verification'):
    serializer = get_serializer()
    return serializer.dumps(email, salt=salt)

def verify_token(token, salt='email-verification', max_age=86400):  # 24 hours
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt=salt, max_age=max_age)
        return email
    except (SignatureExpired, BadTimeSignature, BadSignature):
        return None

def is_domain_allowed(email):
    """Checks whether the user's email domain belongs to the configured allowlist."""
    if '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    allowed_domains = current_app.config.get('CAMPUS_EMAIL_DOMAINS', [])
    allowed = [d.strip().lower() for d in allowed_domains if d.strip()]
    
    # If no allowlist is configured or wildcard, allow
    if not allowed or '*' in allowed:
        return True
        
    return domain in allowed

def send_email(subject, recipient, text_body, html_body=None):
    """
    Sends an email using Flask-Mail.
    If mail credentials are not configured or mail server is localhost/unreachable,
    logs the entire email to the console in development mode so developers and testers
    can immediately click verification and password-reset links!
    """
    # Check if mail server is set up
    mail_server = current_app.config.get('MAIL_SERVER')
    has_credentials = bool(current_app.config.get('MAIL_USERNAME'))
    
    # In development mode or missing mail credentials, print directly to console
    if current_app.config.get('DEBUG') or not has_credentials or mail_server in ['localhost', '127.0.0.1']:
        print("="*70)
        print("[CAMPUSCONNECT EMAIL SERVICE - LOCAL CONSOLE LOG]")
        print(f"TO:      {recipient}")
        print(f"SUBJECT: {subject}")
        print("-" * 70)
        print(text_body)
        print("="*70 + "\n")
        return True
        
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=text_body,
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[EmailService Error] Failed to send email to {recipient}: {e}")
        # Always log to console as fallback so flows don't crash
        print(f"Fallback Console Message:\n{text_body}")
        return False

def send_verification_email(user):
    """Generates verification link and sends verification email."""
    token = generate_token(user.email, salt='email-verification')
    user.verification_token = token
    
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    subject = "Verify Your CampusConnect University Account"
    
    text_body = f"""Hello {user.full_name},

Thank you for registering on CampusConnect – Smart Campus Lost & Found Portal.

Please verify your university email address by clicking the link below:
{verify_url}

This verification link will expire in 24 hours.

If you did not create this account, please ignore this email.

Best regards,
The CampusConnect Team
"""
    return send_email(subject, user.email, text_body)

def send_password_reset_email(user):
    """Generates password reset link and sends reset email."""
    token = generate_token(user.email, salt='password-reset')
    user.reset_token = token
    
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    subject = "CampusConnect Password Reset Request"
    
    text_body = f"""Hello {user.full_name},

We received a request to reset your password on CampusConnect.

Please click the link below to set a new password:
{reset_url}

This link is valid for 1 hour. If you did not request a password reset, please ignore this email.

Best regards,
The CampusConnect Team
"""
    return send_email(subject, user.email, text_body)

