from datetime import datetime
from app.extensions import db
from app.models.claim import Claim
from app.models.report import FoundReport, LostReport
from app.models.message import Conversation
from app.models.notification import AuditLog
from app.services.notification_service import create_notification, notify_admins
from app.services.image_service import save_evidence_document

def generate_claim_code():
    year = datetime.utcnow().year
    count = Claim.query.count() + 1
    return f"CLAIM-{year}-{count:05d}"

def submit_claim(user, found_report_id, ownership_description, identifying_answers=None,
                 lost_report_id=None, purchase_date=None, evidence_file=None, contact_method='email'):
    """
    Submits a new ownership claim for a found report.
    Validates eligibility, saves evidence, initializes conversation thread, and notifies admins.
    """
    found_report = FoundReport.query.get(found_report_id)
    if not found_report:
        return None, "Found item report not found."
        
    if found_report.user_id == user.id:
        return None, "You cannot claim an item you reported as found."
        
    if found_report.report_status in ['returned', 'closed']:
        return None, "This item has already been returned or resolved."
        
    # Check if this user already has an active claim on this item
    existing = Claim.query.filter_by(
        found_report_id=found_report_id,
        claimant_id=user.id
    ).filter(Claim.claim_status.notin_(['rejected', 'cancelled'])).first()
    
    if existing:
        return None, f"You already have an active claim ({existing.claim_code}) for this item."
        
    # Process evidence file if provided
    evidence_path = None
    if evidence_file and hasattr(evidence_file, 'filename') and evidence_file.filename:
        evidence_path = save_evidence_document(evidence_file)
        
    claim_code = generate_claim_code()
    
    claim = Claim(
        claim_code=claim_code,
        lost_report_id=lost_report_id,
        found_report_id=found_report_id,
        claimant_id=user.id,
        ownership_description=ownership_description,
        identifying_answers=identifying_answers,
        approximate_purchase_date=purchase_date,
        evidence_path=evidence_path,
        contact_method=contact_method,
        claim_status='submitted'
    )
    db.session.add(claim)
    db.session.flush()  # To get claim.id
    
    # Create associated secure conversation thread
    convo = Conversation(claim_id=claim.id)
    db.session.add(convo)
    
    # Audit log
    audit = AuditLog(
        actor_id=user.id,
        action='claim_submitted',
        entity_type='claim',
        entity_id=str(claim.id),
        details=f"Claim {claim_code} submitted for item '{found_report.item_name}' ({found_report.report_code})"
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify Administrators
    notify_admins(
        title="New Ownership Claim Received",
        message=f"User {user.full_name} submitted claim {claim_code} for item '{found_report.item_name}' ({found_report.report_code}).",
        notification_type='claim_submitted',
        link_url=f"/admin/claims/{claim.id}",
        related_claim_id=claim.id
    )
    
    # Notify Claimant
    create_notification(
        user_id=user.id,
        title="Claim Submitted Successfully",
        message=f"Your claim {claim_code} for '{found_report.item_name}' has been received and is pending administrator review.",
        notification_type='claim_status',
        link_url=f"/claims/{claim.id}",
        related_claim_id=claim.id
    )
    
    return claim, None

def review_claim(claim_id, admin_user, new_status, review_notes=None, rejection_reason=None):
    """
    Updates claim status with review notes, rejection reasoning, and audit logging.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        return False, "Claim not found."
        
    valid_statuses = ['submitted', 'under_review', 'evidence_required', 'approved', 'rejected', 'handover_scheduled', 'returned', 'cancelled']
    if new_status not in valid_statuses:
        return False, "Invalid claim status."
        
    if new_status == 'rejected' and not rejection_reason:
        return False, "A rejection reason is mandatory when rejecting a claim."
        
    claim.claim_status = new_status
    claim.reviewed_by = admin_user.id
    if review_notes:
        claim.review_notes = review_notes
    if rejection_reason:
        claim.rejection_reason = rejection_reason
        
    # If approved, lock the found report
    if new_status == 'approved':
        claim.found_report.report_status = 'claimed'
        
    # Audit log
    audit = AuditLog(
        actor_id=admin_user.id,
        action=f"claim_{new_status}",
        entity_type='claim',
        entity_id=str(claim.id),
        details=f"Admin {admin_user.full_name} updated claim {claim.claim_code} to {new_status}. Notes: {review_notes or rejection_reason or 'None'}"
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify Claimant
    status_messages = {
        'under_review': "Your claim is currently under review by our campus administrators.",
        'evidence_required': f"Additional ownership evidence is required for your claim: {review_notes or 'Please check messages.'}",
        'approved': "Congratulations! Your ownership claim has been approved. A handover appointment will be scheduled shortly.",
        'rejected': f"Your ownership claim has been rejected. Reason: {rejection_reason}",
        'cancelled': "Your claim has been marked as cancelled."
    }
    
    msg = status_messages.get(new_status, f"Your claim status has been updated to {new_status}.")
    create_notification(
        user_id=claim.claimant_id,
        title=f"Claim Status Update: {new_status.replace('_', ' ').title()}",
        message=msg,
        notification_type='claim_status',
        link_url=f"/claims/{claim.id}",
        related_claim_id=claim.id
    )
    
    return True, None

