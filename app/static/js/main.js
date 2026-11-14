// Main client-side script for CampusConnect

document.addEventListener('DOMContentLoaded', () => {
    // 1. Image preview for report upload forms
    const imageInput = document.getElementById('image-upload-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');

    if (imageInput && imagePreview && imagePreviewContainer) {
        imageInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.classList.remove('d-none');
                }
                reader.readAsDataURL(file);
            }
        });

        const removeImageBtn = document.getElementById('remove-image-btn');
        if (removeImageBtn) {
            removeImageBtn.addEventListener('click', () => {
                imageInput.value = '';
                imagePreview.src = '';
                imagePreviewContainer.classList.add('d-none');
            });
        }
    }

    // 2. Notification dropdown mark read actions
    const markAllReadBtn = document.getElementById('mark-all-notifications-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const csrfToken = getCsrfToken();
                const res = await fetch('/api/notifications/read-all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    }
                });
                if (res.ok) {
                    const badge = document.getElementById('notification-badge');
                    if (badge) {
                        badge.classList.add('d-none');
                        badge.textContent = '0';
                    }
                    document.querySelectorAll('.notification-item-unread').forEach(item => {
                        item.classList.remove('notification-item-unread');
                        item.classList.add('text-muted');
                    });
                }
            } catch (err) {
                console.error('Error marking notifications read:', err);
            }
        });
    }

    // 3. Fallback polling for notifications every 30 seconds
    if (window.currentUserAuthenticated) {
        setInterval(pollNotifications, 30000);
    }
});

function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

async function pollNotifications() {
    try {
        const res = await fetch('/api/notifications/poll');
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('notification-badge');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.classList.remove('d-none');
                } else {
                    badge.classList.add('d-none');
                }
            }
        }
    } catch (err) {
        // silent fail on network interruption
    }
}

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toastId = 'toast-' + Date.now();
    const borderStyle = type === 'success' ? 'border-color: rgba(79, 124, 114, 0.4);' :
                        type === 'warning' ? 'border-color: rgba(233, 196, 106, 0.5);' :
                        type === 'danger' ? 'border-color: rgba(217, 140, 104, 0.4);' : 'border-color: rgba(36, 59, 83, 0.3);';

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center bg-white border mb-2 shadow-sm" style="${borderStyle} border-radius: 6px;" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body" style="font-family: 'Lucida Bright', Georgia, serif; font-size: 0.9rem;">
                    <strong style="color: #243B53;">${title}</strong><br/>
                    <span style="color: #39434D;">${message}</span>
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastEl = document.getElementById(toastId);
    if (window.bootstrap && window.bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastEl, { delay: 6000 });
        toast.show();
    }
}
