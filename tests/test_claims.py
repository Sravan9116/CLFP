import pytest
from datetime import date, datetime, timedelta
from app.models.report import FoundReport
from app.models.claim import Claim
from app.models.handover import Handover
from app.models.user import User
from app.services.claim_service import submit_claim, review_claim
from app.services.handover_service import schedule_handover, complete_handover, claimant_confirm_handover

def test_claim_submission_and_workflow(app, sample_user, sample_admin):
    with app.app_context():
        # Create finder user
        finder = User(
            full_name="Item Finder",
            email="finder@campusconnect.edu",
            institutional_id="STU-0002",
            role="user"
        )
        finder.set_password("Pass123!")
        from app.extensions import db
        db.session.add(finder)
        db.session.commit()

        # Create found report
        found = FoundReport(
            report_code="FOUND-TEST-01",
            user_id=finder.id,
            category_id=1,
            item_name="Hydro Flask Bottle",
            description="Black water bottle",
            primary_color="Black",
            date_found=date.today(),
            location_id=1,
            custody_status="security_office",
            review_status="approved",
            report_status="active"
        )
        db.session.add(found)
        db.session.commit()

        # 1. Claimant cannot claim their own found report
        claim_self, err_self = submit_claim(finder, found.id, "It is mine")
        assert claim_self is None
        assert "cannot claim an item you reported" in err_self

        # 2. Legitimate user submits claim
        claim, err = submit_claim(
            user=sample_user,
            found_report_id=found.id,
            ownership_description="Lost my bottle yesterday during lunch.",
            identifying_answers="Small dent on base and blue silicone boot.",
            purchase_date="January 2025"
        )
        assert err is None
        assert claim is not None
        assert claim.claim_status == "submitted"
        assert claim.claim_code.startswith("CLAIM-")

        # 3. Admin requests additional evidence
        ok, _ = review_claim(claim.id, sample_admin, "evidence_required", review_notes="Upload receipt")
        assert ok is True
        assert claim.claim_status == "evidence_required"

        # 4. Admin rejects without reason should fail
        ok_fail, err_fail = review_claim(claim.id, sample_admin, "rejected", rejection_reason="")
        assert ok_fail is False
        assert "mandatory" in err_fail

        # 5. Admin approves claim
        ok_app, _ = review_claim(claim.id, sample_admin, "approved", review_notes="Answers verified")
        assert ok_app is True
        assert claim.claim_status == "approved"
        assert found.report_status == "claimed"

        # 6. Admin schedules handover
        handover, err_h = schedule_handover(
            claim_id=claim.id,
            scheduled_location_id=1,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            admin_user=sample_admin,
            notes="Meet at desk"
        )
        assert err_h is None
        assert handover is not None
        assert handover.recovery_code.startswith("REC-")
        assert claim.claim_status == "handover_scheduled"

        # 7. Claimant confirms appointment
        ok_conf, _ = claimant_confirm_handover(handover.id, sample_user)
        assert ok_conf is True
        assert handover.claimant_confirmed is True

        # 8. Admin completes in-person handover
        ok_done, _ = complete_handover(handover.id, sample_admin)
        assert ok_done is True
        assert handover.handover_status == "completed"
        assert claim.claim_status == "returned"
        assert found.report_status == "returned"

