import pytest
from app.models.user import User
from app.services.email_service import is_domain_allowed, generate_token, verify_token

def test_domain_allowlist(app):
    with app.app_context():
        assert is_domain_allowed("user@campusconnect.edu") is True
        assert is_domain_allowed("student@student.campusconnect.edu") is True
        assert is_domain_allowed("hacker@malicious-external-site.com") is False

def test_token_generation_and_verification(app):
    with app.app_context():
        token = generate_token("test@campusconnect.edu", salt="email-verification")
        email = verify_token(token, salt="email-verification", max_age=3600)
        assert email == "test@campusconnect.edu"

        # Invalid token returns None
        assert verify_token("invalid-garbage-token", salt="email-verification") is None

def test_user_registration(client, app):
    res = client.post('/auth/register', data={
        'full_name': 'New Student',
        'email': 'new.student@campusconnect.edu',
        'institutional_id': 'STU-1234',
        'department_id': 1,
        'user_type': 'student',
        'year_of_study': 2,
        'password': 'SecurePassword2026!',
        'confirm_password': 'SecurePassword2026!'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        u = User.query.filter_by(email='new.student@campusconnect.edu').first()
        assert u is not None
        assert u.role == 'user'
        assert u.check_password('SecurePassword2026!') is True

def test_registration_domain_restriction(client):
    res = client.post('/auth/register', data={
        'full_name': 'Unauthorized User',
        'email': 'user@gmail.com',  # Disallowed external domain
        'institutional_id': 'EXT-9999',
        'department_id': 1,
        'user_type': 'student',
        'password': 'SecurePassword2026!',
        'confirm_password': 'SecurePassword2026!'
    }, follow_redirects=True)
    assert b'Registration is restricted to authorized campus email domains' in res.data

def test_user_login_and_logout(client, sample_user):
    # Valid login
    res = client.post('/auth/login', data={
        'email': sample_user.email,
        'password': 'StudentPass123!'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'My Dashboard' in res.data or b'Welcome back' in res.data

    # Logout
    res_logout = client.get('/auth/logout', follow_redirects=True)
    assert b'You have been logged out' in res_logout.data

def test_invalid_login_credentials(client, sample_user):
    res = client.post('/auth/login', data={
        'email': sample_user.email,
        'password': 'WrongPassword!'
    }, follow_redirects=True)
    assert b'Invalid email address or password' in res.data

