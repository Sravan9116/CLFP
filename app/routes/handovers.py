from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, send_file
from flask_login import login_required, current_user
from app.models.handover import Handover
from app.models.claim import Claim
from app.services.handover_service import (
    claimant_confirm_handover,
    complete_handover,
    generate_recovery_pdf_receipt
)

handovers_bp = Blueprint('handovers', __name__, url_prefix='/handovers')

@handovers_bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
def confirm(id):
    success, error = claimant_confirm_handover(id, current_user)
    if not success:
        flash(error or 'Failed to confirm appointment.', 'danger')
    else:
        flash('Handover appointment confirmed! Please bring your physical institutional ID to the recovery location.', 'success')
    return redirect(request.referrer or url_for('claims.my_claims'))

@handovers_bp.route('/<int:id>/receipt')
@login_required
def download_receipt(id):
    handover = Handover.query.get_or_404(id)
    claim = handover.claim
    
    # Permission: claimant or admin
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    pdf_buffer = generate_recovery_pdf_receipt(handover.id)
    if not pdf_buffer:
        flash('Receipt could not be generated.', 'danger')
        return redirect(url_for('claims.view_claim', id=claim.id))
        
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"CampusConnect_Receipt_{handover.recovery_code}.pdf"
    )

@handovers_bp.route('/verify/<string:recovery_code>')
def verify_receipt(recovery_code):
    """
    Publicly safe verification page scanned via QR code on recovery receipt.
    Does NOT expose personal addresses, phone numbers, or private answers.
    """
    handover = Handover.query.filter_by(recovery_code=recovery_code).first_or_404()
    claim = handover.claim
    found_item = claim.found_report
    
    return render_template(
        'handover/verify.html',
        handover=handover,
        claim=claim,
        found_item=found_item
    )

