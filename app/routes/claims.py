from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.claim import Claim
from app.models.report import FoundReport, LostReport
from app.models.notification import AuditLog
from app.services.claim_service import submit_claim, review_claim
from app.services.image_service import save_evidence_document

claims_bp = Blueprint('claims', __name__, url_prefix='/claims')

@claims_bp.route('/my-claims')
@login_required
def my_claims():
    claims = Claim.query.filter_by(claimant_id=current_user.id).order_by(Claim.created_at.desc()).all()
    return render_template('claims/my_claims.html', claims=claims)

@claims_bp.route('/submit/<int:found_report_id>', methods=['GET', 'POST'])
@login_required
def submit(found_report_id):
    found_item = FoundReport.query.get_or_404(found_report_id)
    
    # Check if user owns found report
    if found_item.user_id == current_user.id:
        flash('You cannot submit an ownership claim on an item that you reported finding.', 'danger')
        return redirect(url_for('reports.view_found', id=found_item.id))
        
    # User's lost reports in same category to optionally link
    user_lost_reports = LostReport.query.filter_by(
        user_id=current_user.id,
        category_id=found_item.category_id,
        report_status='active'
    ).all()
    
    if request.method == 'POST':
        ownership_description = request.form.get('ownership_description', '').strip()
        identifying_answers = request.form.get('identifying_answers', '').strip()
        purchase_date = request.form.get('purchase_date', '').strip()
        lost_report_id = request.form.get('lost_report_id')
        contact_method = request.form.get('contact_method', 'email')
        
        evidence_file = request.files.get('evidence_file')
        
        if not ownership_description:
            flash('Please describe your item and ownership details clearly.', 'danger')
            return render_template('claims/submit_claim.html', found_item=found_item, user_lost_reports=user_lost_reports)
            
        claim, error = submit_claim(
            user=current_user,
            found_report_id=found_item.id,
            ownership_description=ownership_description,
            identifying_answers=identifying_answers,
            lost_report_id=int(lost_report_id) if (lost_report_id and lost_report_id.isdigit()) else None,
            purchase_date=purchase_date,
            evidence_file=evidence_file,
            contact_method=contact_method
        )
        
        if error:
            flash(error, 'danger')
            return render_template('claims/submit_claim.html', found_item=found_item, user_lost_reports=user_lost_reports)
            
        flash(f'Ownership claim {claim.claim_code} has been successfully submitted! A campus administrator will review your evidence.', 'success')
        return redirect(url_for('claims.view_claim', id=claim.id))
        
    return render_template('claims/submit_claim.html', found_item=found_item, user_lost_reports=user_lost_reports)

@claims_bp.route('/<int:id>')
@login_required
def view_claim(id):
    claim = Claim.query.get_or_404(id)
    
    # Permission check: Claimant or Administrator only
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    return render_template('claims/claim_detail.html', claim=claim)

@claims_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_claim(id):
    claim = Claim.query.get_or_404(id)
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    if claim.claim_status in ['returned', 'completed']:
        flash('Completed recovery claims cannot be cancelled.', 'danger')
        return redirect(url_for('claims.view_claim', id=claim.id))
        
    claim.claim_status = 'cancelled'
    audit = AuditLog(
        actor_id=current_user.id,
        action='claim_cancelled',
        entity_type='claim',
        entity_id=str(claim.id),
        details=f"Claim {claim.claim_code} cancelled by {current_user.full_name}."
    )
    db.session.add(audit)
    db.session.commit()
    
    flash(f'Claim {claim.claim_code} has been cancelled.', 'info')
    return redirect(url_for('claims.my_claims'))

@claims_bp.route('/<int:id>/upload-evidence', methods=['POST'])
@login_required
def upload_evidence(id):
    claim = Claim.query.get_or_404(id)
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    file = request.files.get('additional_evidence')
    if not file or not file.filename:
        flash('No file selected.', 'warning')
        return redirect(url_for('claims.view_claim', id=claim.id))
        
    saved_path = save_evidence_document(file)
    if not saved_path:
        flash('Invalid document or image format. Please upload JPG, PNG, or PDF.', 'danger')
        return redirect(url_for('claims.view_claim', id=claim.id))
        
    claim.evidence_path = saved_path
    if claim.claim_status == 'evidence_required':
        claim.claim_status = 'under_review'
        
    audit = AuditLog(
        actor_id=current_user.id,
        action='claim_evidence_uploaded',
        entity_type='claim',
        entity_id=str(claim.id),
        details=f"Additional evidence document uploaded for claim {claim.claim_code}."
    )
    db.session.add(audit)
    db.session.commit()
    
    flash('Additional ownership evidence uploaded successfully. Administrator notified.', 'success')
    return redirect(url_for('claims.view_claim', id=claim.id))

