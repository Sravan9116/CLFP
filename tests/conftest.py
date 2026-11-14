import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Department
from app.models.report import CampusLocation, ItemCategory, LostReport, FoundReport
from app.models.claim import Claim
from datetime import date, timedelta

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Seed basic department & category
        dept = Department(department_name="Computer Science", department_code="CSE", status="active")
        cat = ItemCategory(category_name="Electronics", icon_class="bi-laptop", status="active")
        loc = CampusLocation(location_name="Main Library", location_category="Library", latitude=42.3601, longitude=-71.0942, status="active")
        db.session.add_all([dept, cat, loc])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_user(app):
    user = User(
        full_name="Test Student",
        email="student@campusconnect.edu",
        institutional_id="STU-9999",
        role="user",
        user_type="student",
        email_verified=True,
        account_status="active"
    )
    user.set_password("StudentPass123!")
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def sample_admin(app):
    admin = User(
        full_name="Admin Officer",
        email="admin@campusconnect.edu",
        institutional_id="ADM-8888",
        role="admin",
        user_type="staff",
        email_verified=True,
        account_status="active"
    )
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()
    return admin

