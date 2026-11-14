import os
from datetime import datetime
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as ReportLabImage
from flask import current_app, url_for
from app.extensions import db
from app.models.handover import Handover
from app.models.claim import Claim
from app.models.notification import AuditLog
from app.services.notification_service import create_notification, notify_admins

def generate_recovery_code():
    year = datetime.utcnow().year
    count = Handover.query.count() + 1
    return f"REC-{year}-{count:05d}"

def schedule_handover(claim_id, scheduled_location_id, scheduled_at, admin_user, notes=None):
    """
    Schedules an in-person item recovery handover, generates a QR code verification token.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        return None, "Claim not found."
        
    if claim.claim_status != 'approved':
        return None, "Only approved claims can have a handover scheduled."
        
    # Check if handover already exists
    handover = Handover.query.filter_by(claim_id=claim_id).first()
    recovery_code = handover.recovery_code if handover else generate_recovery_code()
    
    # Generate QR Code image
    qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    qr_filename = f"qr_{recovery_code}.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    
    verify_url = f"/handovers/verify/{recovery_code}"
    
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_path)
    
    relative_qr_path = f"uploads/qrcodes/{qr_filename}"
    
    if not handover:
        handover = Handover(
            claim_id=claim.id,
            recovery_code=recovery_code,
            scheduled_location_id=scheduled_location_id,
            scheduled_at=scheduled_at,
            claimant_confirmed=False,
            administrator_confirmed=False,
            handover_status='scheduled',
            notes=notes,
            qr_code_path=relative_qr_path
        )
        db.session.add(handover)
    else:
        handover.scheduled_location_id = scheduled_location_id
        handover.scheduled_at = scheduled_at
        handover.notes = notes
        handover.qr_code_path = relative_qr_path
        handover.handover_status = 'scheduled'
        
    claim.claim_status = 'handover_scheduled'
    
    audit = AuditLog(
        actor_id=admin_user.id,
        action='handover_scheduled',
        entity_type='handover',
        entity_id=str(handover.id if handover.id else recovery_code),
        details=f"Handover {recovery_code} scheduled at {handover.location.location_name if handover.location else scheduled_location_id} for {scheduled_at}."
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify Claimant
    loc_name = handover.location.location_name if handover.location else "Designated Campus Point"
    create_notification(
        user_id=claim.claimant_id,
        title="Item Handover Scheduled",
        message=f"Handover scheduled for your item '{claim.found_report.item_name}' at {loc_name} on {scheduled_at.strftime('%Y-%m-%d %H:%M')}. Please confirm your appointment in your dashboard.",
        notification_type='handover_scheduled',
        link_url=f"/claims/{claim.id}",
        related_claim_id=claim.id
    )
    
    return handover, None

def claimant_confirm_handover(handover_id, user):
    """Claimant confirms appointment availability."""
    handover = Handover.query.get(handover_id)
    if not handover or handover.claim.claimant_id != user.id:
        return False, "Unauthorized or handover not found."
        
    handover.claimant_confirmed = True
    handover.handover_status = 'confirmed_by_claimant'
    
    audit = AuditLog(
        actor_id=user.id,
        action='handover_claimant_confirmed',
        entity_type='handover',
        entity_id=str(handover.id),
        details=f"Claimant {user.full_name} confirmed handover appointment {handover.recovery_code}."
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify admin
    notify_admins(
        title="Claimant Confirmed Handover Appointment",
        message=f"Claimant {user.full_name} confirmed appointment {handover.recovery_code}.",
        notification_type='handover_confirmed',
        link_url=f"/admin/claims/{handover.claim_id}",
        related_claim_id=handover.claim_id
    )
    return True, None

def complete_handover(handover_id, admin_user):
    """
    Administrator marks in-person verification complete and marks item as returned.
    """
    handover = Handover.query.get(handover_id)
    if not handover:
        return False, "Handover record not found."
        
    handover.administrator_confirmed = True
    handover.verified_by_admin_id = admin_user.id
    handover.handover_status = 'completed'
    handover.completed_at = datetime.utcnow()
    
    # Update Claim and Reports
    claim = handover.claim
    claim.claim_status = 'returned'
    
    # Mark found report as returned
    if claim.found_report:
        claim.found_report.report_status = 'returned'
        
    # Mark linked lost report as resolved if present
    if claim.lost_report:
        claim.lost_report.report_status = 'resolved'
        
    audit = AuditLog(
        actor_id=admin_user.id,
        action='handover_completed',
        entity_type='handover',
        entity_id=str(handover.id),
        details=f"Admin {admin_user.full_name} verified identity and marked handover {handover.recovery_code} as COMPLETED. Item returned to {claim.claimant.full_name}."
    )
    db.session.add(audit)
    db.session.commit()
    
    # Notify Claimant
    create_notification(
        user_id=claim.claimant_id,
        title="Item Recovery Completed",
        message=f"Your handover {handover.recovery_code} has been successfully completed and the item is marked as returned. You can download your official recovery receipt.",
        notification_type='handover_completed',
        link_url=f"/claims/{claim.id}",
        related_claim_id=claim.id
    )
    return True, None

def generate_recovery_pdf_receipt(handover_id):
    """
    Generates a formal, professional PDF recovery receipt using ReportLab.
    """
    handover = Handover.query.get(handover_id)
    if not handover:
        return None
        
    claim = handover.claim
    claimant = claim.claimant
    found_item = claim.found_report
    lost_item = claim.lost_report
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#14213D'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    normal_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#1F2937'),
        leading=14
    )
    
    bold_style = ParagraphStyle(
        'BoldBody',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("CAMPUSCONNECT", title_style))
    elements.append(Paragraph("Smart Campus Lost & Found Portal • Official Item Recovery Receipt", subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Summary Bar Table
    summary_data = [
        [Paragraph("<b>Receipt Code:</b>", normal_style), Paragraph(f"<b>{handover.recovery_code}</b>", bold_style),
         Paragraph("<b>Date of Handover:</b>", normal_style), Paragraph(handover.completed_at.strftime('%Y-%m-%d %H:%M') if handover.completed_at else 'Scheduled', normal_style)],
        [Paragraph("<b>Claim ID:</b>", normal_style), Paragraph(claim.claim_code, normal_style),
         Paragraph("<b>Verification Status:</b>", normal_style), Paragraph(f"<b>{handover.handover_status.upper()}</b>", bold_style)]
    ]
    summary_table = Table(summary_data, colWidths=[120, 140, 120, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 15))
    
    # Item Details Table
    elements.append(Paragraph("Recovered Item Details", section_style))
    item_data = [
        [Paragraph("Item Name:", bold_style), Paragraph(found_item.item_name, normal_style)],
        [Paragraph("Category:", bold_style), Paragraph(found_item.category.category_name if found_item.category else 'N/A', normal_style)],
        [Paragraph("Brand / Model:", bold_style), Paragraph(found_item.brand or 'Unspecified', normal_style)],
        [Paragraph("Primary Color:", bold_style), Paragraph(found_item.primary_color, normal_style)],
        [Paragraph("Found Report Code:", bold_style), Paragraph(found_item.report_code, normal_style)],
        [Paragraph("Lost Report Code:", bold_style), Paragraph(lost_item.report_code if lost_item else 'Direct Claim (No Lost Report)', normal_style)],
        [Paragraph("Handover Location:", bold_style), Paragraph(handover.location.location_name if handover.location else 'Campus Security Office', normal_style)],
    ]
    item_table = Table(item_data, colWidths=[160, 370])
    item_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 15))
    
    # Claimant & Administrator Details
    elements.append(Paragraph("Parties Involved", section_style))
    parties_data = [
        [Paragraph("Claimant Name:", bold_style), Paragraph(claimant.full_name, normal_style)],
        [Paragraph("Institutional ID:", bold_style), Paragraph(claimant.institutional_id, normal_style)],
        [Paragraph("University Email:", bold_style), Paragraph(claimant.email, normal_style)],
        [Paragraph("Department:", bold_style), Paragraph(claimant.department.department_name if claimant.department else 'N/A', normal_style)],
        [Paragraph("Verified By Administrator:", bold_style), Paragraph(handover.verified_by_admin.full_name if handover.verified_by_admin else 'Campus Administrator', normal_style)],
        [Paragraph("Identity Checked In-Person:", bold_style), Paragraph("YES - Institutional Photo ID Verified", bold_style)]
    ]
    parties_table = Table(parties_data, colWidths=[160, 370])
    parties_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 15))
    
    # QR Code & Signatures
    qr_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qrcodes', f"qr_{handover.recovery_code}.png")
    
    elements.append(Paragraph("Verification & Signatures", section_style))
    
    if os.path.exists(qr_full_path):
        qr_img = ReportLabImage(qr_full_path, width=90, height=90)
    else:
        qr_img = Paragraph("QR Verification Available Online", normal_style)
        
    sig_data = [
        [
            qr_img,
            Paragraph("<b>Claimant Confirmation:</b><br/><br/>___________________________<br/>Date: ____________________", normal_style),
            Paragraph("<b>Administrator Signature:</b><br/><br/>___________________________<br/>Date: ____________________", normal_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[110, 210, 210])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 15))
    
    # Footer Notice
    footer_text = "This document constitutes official campus proof of item recovery under university property policy. Fraudulent claims are subject to academic disciplinary and legal action."
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#6B7280'))))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

