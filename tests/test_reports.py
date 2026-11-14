import pytest
from app.models.report import LostReport, FoundReport
from datetime import date

def login_client(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)

def test_report_lost_item(client, sample_user, app):
    login_client(client, sample_user.email, 'StudentPass123!')

    res = client.post('/reports/lost/new', data={
        'item_name': 'Black Noise Canceling Headphones',
        'category_id': 1,
        'description': 'Left on the 2nd floor library study desk.',
        'brand': 'Sony',
        'primary_color': 'Black',
        'secondary_color': 'Silver',
        'date_lost': '2026-03-10',
        'approximate_time': '15:00',
        'location_id': 1,
        'identifying_features': 'Serial #SN-998822 on left ear cup'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        report = LostReport.query.filter_by(item_name='Black Noise Canceling Headphones').first()
        assert report is not None
        assert report.report_code.startswith('LOST-')
        assert report.review_status == 'pending_review'
        assert report.user_id == sample_user.id

def test_report_found_item(client, sample_user, app):
    login_client(client, sample_user.email, 'StudentPass123!')

    res = client.post('/reports/found/new', data={
        'item_name': 'Blue Water Bottle',
        'category_id': 1,
        'description': 'Found near the water fountain.',
        'brand': 'Hydro Flask',
        'primary_color': 'Blue',
        'date_found': '2026-03-11',
        'location_id': 1,
        'custody_status': 'security_office',
        'custody_location': 'Desk Locker 2',
        'identifying_features': 'Scratch on base'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        report = FoundReport.query.filter_by(item_name='Blue Water Bottle').first()
        assert report is not None
        assert report.report_code.startswith('FOUND-')
        assert report.custody_status == 'security_office'

def test_admin_approve_and_reject_report(client, sample_admin, sample_user, app):
    with app.app_context():
        report = LostReport(
            report_code="LOST-2026-99999",
            user_id=sample_user.id,
            category_id=1,
            item_name="Silver Laptop",
            description="Dell XPS 13 inch",
            primary_color="Silver",
            date_lost=date.today(),
            location_id=1,
            review_status="pending_review",
            report_status="active"
        )
        from app.extensions import db
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    # Log in as admin
    login_client(client, sample_admin.email, 'AdminPass123!')

    # Approve
    res_approve = client.post(f'/admin/reports/lost/{report_id}/approve', follow_redirects=True)
    assert res_approve.status_code == 200

    with app.app_context():
        updated = LostReport.query.get(report_id)
        assert updated.review_status == 'approved'

    # Reject
    res_reject = client.post(f'/admin/reports/lost/{report_id}/reject', data={'reason': 'Inappropriate description'}, follow_redirects=True)
    assert res_reject.status_code == 200

    with app.app_context():
        rejected = LostReport.query.get(report_id)
        assert rejected.review_status == 'rejected'
        assert rejected.rejection_reason == 'Inappropriate description'

