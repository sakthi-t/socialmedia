// Enhanced messaging functionality

// Auto-refresh messages
let lastMessageId = 0;
let currentChatUserId = null;
let pollingInterval = null;

function startPolling(userId) {
    currentChatUserId = userId;
    lastMessageId = document.querySelector('.message')?.lastElementChild?.dataset.messageId || 0;

    // Clear any existing interval
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Start polling every 3 seconds
    pollingInterval = setInterval(() => {
        fetch(`/api/messages/${userId}/latest?last_id=${lastMessageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.messages && data.messages.length > 0) {
                    appendNewMessages(data.messages);
                }
            })
            .catch(error => console.error('Error fetching messages:', error));
    }, 3000);
}

function appendNewMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');

    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.sender_id === window.currentUserId ? 'sent' : 'received'}`;
        messageDiv.dataset.messageId = msg.id;

        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';

        if (msg.sender_id !== window.currentUserId) {
            const messageInfo = document.createElement('div');
            messageInfo.className = 'message-info';

            const senderName = document.createElement('span');
            senderName.className = 'message-sender';
            senderName.textContent = msg.sender_name;

            messageInfo.appendChild(senderName);
            messageBubble.appendChild(messageInfo);
        }

        const content = document.createElement('div');
        content.textContent = msg.content;

        const time = document.createElement('div');
        time.className = 'message-time';
        const timeObj = new Date(msg.timestamp);
        time.textContent = timeObj.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        messageBubble.appendChild(content);
        messageBubble.appendChild(time);
        messageDiv.appendChild(messageBubble);

        chatMessages.appendChild(messageDiv);
        lastMessageId = msg.id;
    });

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Update unread count notification
function updateUnreadCount() {
    fetch('/api/unread-count')
        .then(response => response.json())
        .then(data => {
            const unreadCount = document.getElementById('unreadCount');
            if (unreadCount) {
                if (data.count > 0) {
                    unreadCount.textContent = data.count;
                    unreadCount.classList.remove('d-none');
                } else {
                    unreadCount.classList.add('d-none');
                }
            }
        })
        .catch(error => console.error('Error fetching unread count:', error));
}

// Check for new messages periodically (when not in chat)
setInterval(() => {
    if (!currentChatUserId) {
        updateUnreadCount();
    }
}, 5000);

// Stop polling when leaving page
window.addEventListener('beforeunload', () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});