import pytest
from app.models.user import User
from app.models.report import FoundReport
from app.models.claim import Claim
from datetime import date

def test_unauthenticated_access_protection(client):
    res = client.get('/user/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']

def test_non_admin_cannot_access_admin_portal(client, sample_user):
    client.post('/auth/login', data={'email': sample_user.email, 'password': 'StudentPass123!'}, follow_redirects=True)
    res = client.get('/admin/dashboard')
    # Should be 403 Forbidden
    assert res.status_code == 403

def test_user_cannot_self_promote_role_on_registration(client, app):
    client.post('/auth/register', data={
        'full_name': 'Sneaky User',
        'email': 'sneaky@campusconnect.edu',
        'institutional_id': 'STU-9900',
        'department_id': 1,
        'user_type': 'student',
        'role': 'super_admin',  # Attempted privilege escalation
        'password': 'SecurePass2026!',
        'confirm_password': 'SecurePass2026!'
    }, follow_redirects=True)

    with app.app_context():
        u = User.query.filter_by(email='sneaky@campusconnect.edu').first()
        assert u is not None
        assert u.role == 'user'  # Server-side enforcement overrides injected role

def test_idor_claim_protection(client, sample_user, app):
    with app.app_context():
        other_user = User(
            full_name="Other Student",
            email="other@campusconnect.edu",
            institutional_id="STU-7777",
            role="user"
        )
        other_user.set_password("Pass123!")
        from app.extensions import db
        db.session.add(other_user)
        db.session.commit()

        found = FoundReport(
            report_code="FOUND-IDOR-01",
            user_id=other_user.id,
            category_id=1,
            item_name="Keys",
            description="Keys",
            primary_color="Silver",
            date_found=date.today(),
            location_id=1,
            review_status="approved",
            report_status="active"
        )
        db.session.add(found)
        db.session.commit()

        # Create claim owned by other_user
        claim = Claim(
            claim_code="CLAIM-PRIVATE-01",
            found_report_id=found.id,
            claimant_id=other_user.id,
            ownership_description="Private ownership statement",
            identifying_answers="Secret keys",
            claim_status="submitted"
        )
        db.session.add(claim)
        db.session.commit()
        claim_id = claim.id

    # Log in as sample_user (not other_user, not admin)
    client.post('/auth/login', data={'email': sample_user.email, 'password': 'StudentPass123!'}, follow_redirects=True)

    # Attempt to access other_user's claim
    res = client.get(f'/claims/{claim_id}')
    assert res.status_code == 403  # Forbidden

