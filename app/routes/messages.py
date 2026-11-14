from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user
from app.extensions import db, socketio
from app.models.claim import Claim
from app.models.message import Conversation, Message
from app.models.notification import AuditLog
from app.services.notification_service import create_notification, notify_admins
from app.services.image_service import save_evidence_document

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')

@messages_bp.route('')
@login_required
def index():
    if current_user.is_admin:
        # Admins see all active claim conversations
        conversations = Conversation.query.join(Claim).order_by(Conversation.updated_at.desc()).all()
    else:
        # Users see conversations for their claims
        conversations = Conversation.query.join(Claim).filter(Claim.claimant_id == current_user.id).order_by(Conversation.updated_at.desc()).all()
        
    return render_template('messages/inbox.html', conversations=conversations)

@messages_bp.route('/claim/<int:claim_id>', methods=['GET', 'POST'])
@login_required
def claim_conversation(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    
    # Security: Only claimant or Admin
    if claim.claimant_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    conversation = Conversation.query.filter_by(claim_id=claim.id).first()
    if not conversation:
        conversation = Conversation(claim_id=claim.id)
        db.session.add(conversation)
        db.session.commit()
        
    # Mark messages from the other party as read
    Message.query.filter(
        Message.conversation_id == conversation.id,
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
    if request.method == 'POST':
        message_text = request.form.get('message_text', '').strip()
        attachment_file = request.files.get('attachment')
        
        if not message_text and not attachment_file:
            flash('Cannot send empty message.', 'warning')
            return redirect(url_for('messages.claim_conversation', claim_id=claim.id))
            
        attachment_path = None
        if attachment_file and attachment_file.filename:
            attachment_path = save_evidence_document(attachment_file)
            
        msg = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            message_text=message_text or 'Sent an attachment.',
            attachment_path=attachment_path,
            is_read=False
        )
        conversation.updated_at = datetime.utcnow()
        db.session.add(msg)
        db.session.commit()
        
        # Real-time message emission via SocketIO to claim room
        payload = msg.to_dict()
        try:
            socketio.emit('new_message', payload, room=f"claim_{claim.id}")
        except Exception:
            pass
            
        # Notification to other party
        if current_user.is_admin:
            # Notify claimant
            create_notification(
                user_id=claim.claimant_id,
                title="New Message from Campus Administration",
                message=f"Administrator {current_user.full_name} sent a message regarding claim {claim.claim_code}.",
                notification_type='message',
                link_url=f"/messages/claim/{claim.id}",
                related_claim_id=claim.id
            )
        else:
            # Notify admins
            notify_admins(
                title=f"New Message on Claim {claim.claim_code}",
                message=f"Claimant {current_user.full_name} replied on claim {claim.claim_code}.",
                notification_type='message',
                link_url=f"/messages/claim/{claim.id}",
                related_claim_id=claim.id
            )
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': msg.to_dict()})
            
        return redirect(url_for('messages.claim_conversation', claim_id=claim.id))
        
    messages = conversation.messages.order_by(Message.created_at.asc()).all()
    return render_template('messages/conversation.html', claim=claim, conversation=conversation, messages=messages)

