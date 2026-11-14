// Real-time WebSocket connection handling via Socket.IO

let socket = null;

document.addEventListener('DOMContentLoaded', () => {
    if (typeof io !== 'undefined') {
        socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 2000
        });

        socket.on('connect', () => {
            console.log('Connected to CampusConnect Real-time Socket Server');
        });

        // 1. Personal notification received
        socket.on('new_notification', (data) => {
            console.log('Live Notification:', data);
            incrementNotificationBadge();
            showToast(data.title, data.message, 'success');
            
            try {
                const audio = new Audio('/static/sounds/notification.mp3');
                audio.play().catch(() => {});
            } catch(e) {}
        });

        // 2. Admin Alert received
        socket.on('admin_alert', (data) => {
            console.log('Admin Alert:', data);
            incrementNotificationBadge();
            showToast(`[Admin Alert] ${data.title}`, data.message, 'warning');
        });

        // 3. New message received in conversation
        socket.on('new_message', (data) => {
            console.log('New message received:', data);
            const messagesContainer = document.getElementById('chat-messages-container');
            if (messagesContainer) {
                appendChatMessage(data);
            } else {
                showToast(`New Message from ${data.sender_name}`, data.message_text, 'info');
            }
        });
    }
});

function incrementNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        let count = parseInt(badge.textContent || '0', 10);
        count += 1;
        badge.textContent = count;
        badge.classList.remove('d-none');
    }
}

function appendChatMessage(msg) {
    const messagesContainer = document.getElementById('chat-messages-container');
    if (!messagesContainer) return;

    const currentUserId = window.currentUserId;
    const isMine = (msg.sender_id === currentUserId);

    const alignmentClass = isMine ? 'text-end mb-3' : 'text-start mb-3';
    const bubbleClass = isMine ? 'chat-bubble-sent d-inline-block text-start' : 'chat-bubble-received d-inline-block text-start shadow-sm';

    let attachmentHtml = '';
    if (msg.attachment_path) {
        attachmentHtml = `<div class="mt-2"><a href="/static/${msg.attachment_path}" target="_blank" class="btn btn-sm ${isMine ? 'btn-outline-warm' : 'btn-outline-sage'}"><i class="bi bi-paperclip"></i> View Attachment</a></div>`;
    }

    const html = `
        <div class="${alignmentClass}">
            <div style="max-width: 75%;" class="${bubbleClass}">
                <div class="fw-bold small mb-1 ${isMine ? 'text-white-50' : 'text-muted'}" style="font-size: 0.78rem;">${msg.sender_name} (${msg.sender_role})</div>
                <div style="font-size: 0.93rem;">${msg.message_text}</div>
                ${attachmentHtml}
                <div class="text-end small mt-1 ${isMine ? 'text-white-50' : 'text-muted'}" style="font-size: 0.72rem;">${msg.created_at || 'Just now'}</div>
            </div>
        </div>
    `;

    messagesContainer.insertAdjacentHTML('beforeend', html);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
