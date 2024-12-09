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

// Settings Modal Management
function toggleSettings() {
    const modal = document.getElementById('settingsModal');
    if (modal.style.display === 'block') {
        modal.style.display = 'none';
    } else {
        modal.style.display = 'block';
        loadForgettingSet(); // Load forgetting set when opening settings
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Settings Management
function initializeSettings() {
    // Tab switching
    document.querySelectorAll('.settings-nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.settings-nav-item').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
            item.classList.add('active');
            document.getElementById(item.dataset.tab).classList.add('active');
        });
    });

    // Initialize drag and drop
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    // Hide file input but keep it functional
    fileInput.style.display = 'none';

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });

    // File input change handler
    fileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });

    // Load initial forgetting set
    loadForgettingSet();
}

async function handleFiles(files) {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        // Disable file input during upload
        const fileInput = document.getElementById('fileInput');
        fileInput.disabled = true;

        const response = await fetch('/upload-forgetting-set', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (result.success) {
            showNotification('Files uploaded successfully', 'success');
            await loadForgettingSet();
        } else {
            showNotification(result.error || 'Error uploading files', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showNotification('Error uploading files', 'error');
    } finally {
        // Re-enable file input and reset it
        const fileInput = document.getElementById('fileInput');
        fileInput.disabled = false;
        fileInput.value = '';
    }
}

async function loadForgettingSet() {
    try {
        const response = await fetch('/get-forgetting-set');
        const data = await response.json();
        
        const listContainer = document.getElementById('forgettingSetList');
        const emptyState = document.getElementById('emptyState');
        
        // Clear the list first
        listContainer.innerHTML = '';
        
        // Add empty state back (we'll hide it if we have files)
        listContainer.appendChild(emptyState);
        
        if (data.items && data.items.length > 0) {
            // Hide empty state if we have files
            emptyState.style.display = 'none';
            
            data.items.forEach((item, index) => {
                const itemElement = document.createElement('div');
                itemElement.className = 'file-item';
                itemElement.innerHTML = `
                    <i class="fas fa-file-alt file-icon"></i>
                    <div class="file-name">${item.filename}</div>
                    <div class="file-actions">
                        <button class="file-action-btn" onclick="deleteItem(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
                listContainer.appendChild(itemElement);
            });
        } else {
            emptyState.style.display = 'flex';
        }
    } catch (error) {
        console.error('Error loading forgetting set:', error);
        showNotification('Error loading files', 'error');
    }
}

async function deleteItem(index) {
    try {
        const response = await fetch(`/delete-forgetting-item/${index}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (result.success) {
            showNotification('File deleted successfully', 'success');
            loadForgettingSet(); // Reload the list
        } else {
            showNotification(result.error || 'Error deleting file', 'error');
        }
    } catch (error) {
        console.error('Delete error:', error);
        showNotification('Error deleting file', 'error');
    }
}

function showNotification(message, type = 'info') {
    console.log(`${type}: ${message}`);
    // You can implement a better notification system here
    if (type === 'error') {
        alert(`Error: ${message}`);
    } else if (type === 'success') {
        // Optional: implement a nicer success notification
        console.log(`Success: ${message}`);
    }
}

// Message handling functions
function clearMessages() {
    document.getElementById('chat-messages').innerHTML = '';
}

function loadChat(chatId) {
    if (currentChatId === chatId) return;
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
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
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

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    addMessage(message, true);
    input.value = '';
    input.focus();
    
    // Show typing indicator
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

// Configuration update function
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
        const response = await fetch('/update-config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            button.innerHTML = '<i class="fas fa-check"></i> Saved!';
            setTimeout(() => {
                button.innerHTML = originalText;
            }, 2000);
        } else {
            throw new Error('Failed to update config');
        }
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

// Initialize settings and start first chat when the page loads
window.addEventListener('load', function() {
    initializeSettings();
    startNewChat();
});

// Add this code near your other event listeners
document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('user-input');
    
    function adjustTextareaHeight() {
        textarea.style.height = 'auto';
        // Updated to match new max-height from CSS
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
    
    // Adjust height on input
    textarea.addEventListener('input', adjustTextareaHeight);
    
    // Handle Enter key (Send on Enter, new line on Shift+Enter)
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
            // Reset height after sending
            textarea.style.height = 'auto';
        }
    });
});