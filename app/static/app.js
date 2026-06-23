// Far caster Cleaner - Main Application JavaScript

// API helper
async function api(endpoint, options = {}) {
    const response = await fetch(endpoint, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

// Format relative time
function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show notification
function showNotification(message, type = 'info') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        right: 1rem;
        padding: 0.75rem 1.25rem;
        border-radius: 8px;
        background: ${type === 'error' ? '#EF4444' : type === 'success' ? '#10B981' : '#8B5CF6'};
        color: white;
        font-weight: 500;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Poll for job status updates
async function pollJobStatus(jobId, callback) {
    const poll = async () => {
        try {
            const data = await api(`/api/jobs/${jobId}`);
            callback(data);
            if (data.status === 'running') {
                setTimeout(poll, 2000);
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    };
    poll();
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', () => {
    // Add animation keyframes if not exists
    if (!document.querySelector('#animation-styles')) {
        const style = document.createElement('style');
        style.id = 'animation-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
});
