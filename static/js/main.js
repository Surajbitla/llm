// Chat history management
let chats = [];
let currentChatId = null;

function startNewChat() {
    const chatId = Date.now().toString();
    const chat = {
        id: chatId,
        title: 'New Chat',
        messages: []
    };
    chats.push(chat);
    currentChatId = chatId;
    updateChatHistory();
    clearMessages();
}

function updateChatHistory() {
    const chatHistory = document.getElementById('chatHistory');
    chatHistory.innerHTML = '';
    
    chats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        chatItem.innerHTML = `
            <i class="fas fa-comment"></i>
            <span>${chat.title}</span>
        `;
        chatItem.onclick = () => loadChat(chat.id);
        chatHistory.appendChild(chatItem);
    });
}

function loadChat(chatId) {
    if (currentChatId === chatId) return; // Don't reload if same chat
    
    currentChatId = chatId;
    const chat = chats.find(c => c.id === chatId);
    clearMessages();
    
    if (chat && chat.messages) {
        chat.messages.forEach(msg => {
            addMessage(msg.content, msg.isUser);
        });
    }
    updateChatHistory();
}

function clearMessages() {
    document.getElementById('chat-messages').innerHTML = '';
}

// Message handling
function addMessage(message, isUser) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (!isUser) {
        const formattedMessage = message
            .split('\n\n')
            .map(paragraph => {
                if (paragraph.includes('* ')) {
                    const listItems = paragraph.split('* ').filter(item => item.trim());
                    return `<ul>${listItems.map(item => `<li>${item.trim()}</li>`).join('')}</ul>`;
                }
                else if (/^\d+\./.test(paragraph)) {
                    const listItems = paragraph.split(/\d+\.\s/).filter(item => item.trim());
                    return `<ol>${listItems.map(item => `<li>${item.trim()}</li>`).join('')}</ol>`;
                }
                return `<p>${paragraph}</p>`;
            })
            .join('');
        
        messageDiv.innerHTML = formattedMessage;
    } else {
        messageDiv.textContent = message;
    }
    
    // Start with 0 opacity for fade in effect
    messageDiv.style.opacity = '0';
    chatMessages.appendChild(messageDiv);
    
    // Trigger reflow
    messageDiv.offsetHeight;
    
    // Fade in
    messageDiv.style.transition = 'opacity 0.3s ease-in-out';
    messageDiv.style.opacity = '1';
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Save message to current chat
    if (currentChatId) {
        const chat = chats.find(c => c.id === currentChatId);
        if (chat) {
            chat.messages.push({ content: message, isUser });
            if (chat.messages.length === 1) {
                chat.title = message.slice(0, 30) + (message.length > 30 ? '...' : '');
                updateChatHistory();
            }
        }
    }
}

// Settings modal
function toggleSettings() {
    const modal = document.getElementById('settingsModal');
    modal.style.display = modal.style.display === 'none' ? 'block' : 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Add these functions back to your main.js
function showTypingIndicator() {
    const indicator = document.querySelector('.typing-indicator');
    indicator.classList.remove('hidden');
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.querySelector('.typing-indicator');
    indicator.classList.add('hidden');
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message
    addMessage(message, true);
    input.value = '';
    input.focus(); // Keep focus on input
    
    // Show typing indicator with animated dots
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing';
    typingDiv.innerHTML = `
        <div class="typing-animation">
            <span>Generating response</span>
            <span class="dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
            </span>
        </div>
    `;
    
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message,
                chat_id: currentChatId 
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator with fade out effect
        typingDiv.style.opacity = '0';
        setTimeout(() => {
            typingDiv.remove();
            // Add the actual response with fade in effect
            addMessage(data.response, false);
        }, 300);
        
    } catch (error) {
        typingDiv.remove();
        addMessage('Error: Could not get response', false);
    }
}

async function updateConfig() {
    const button = document.querySelector('.settings-button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    const config = {
        check_before_llm: document.getElementById('checkBeforeLLM').checked,
        similarity_threshold: parseFloat(document.getElementById('similarityThreshold').value),
        model_name: document.getElementById('modelName').value
    };
    
    try {
        await fetch('/update-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        button.innerHTML = '<i class="fas fa-check"></i> Saved!';
        setTimeout(() => {
            button.innerHTML = originalText;
        }, 2000);
    } catch (error) {
        console.error('Error updating config:', error);
        button.innerHTML = '<i class="fas fa-times"></i> Error';
        setTimeout(() => {
            button.innerHTML = originalText;
        }, 2000);
    }
}

// Add event listeners
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

document.getElementById('similarityThreshold').addEventListener('input', function(e) {
    document.getElementById('thresholdValue').textContent = e.target.value;
});

// Initialize first chat on page load
window.onload = function() {
    startNewChat();
};

// Rest of your existing JavaScript... 