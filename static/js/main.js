// Chat history management
let chats = [];
let currentChatId = null;
let chatHistory = {};

function startNewChat() {
    const chatId = Date.now().toString();
    const chat = {
        id: chatId,
        title: 'New Chat',
        messages: []
    };
    chats.push(chat);
    chatHistory[chatId] = [];  // Initialize empty history for new chat
    currentChatId = chatId;
    updateChatHistory();
    clearMessages();
}

function updateChatHistory() {
    const chatHistory = document.getElementById('chatHistory');
    chatHistory.innerHTML = '';
    
    chats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.setAttribute('data-chat-id', chat.id);
        chatItem.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        chatItem.innerHTML = `
            <i class="fas fa-comment"></i>
            <span>${chat.title}</span>
        `;
        chatItem.onclick = () => {
            document.querySelectorAll('.chat-item').forEach(item => {
                item.classList.remove('active');
            });
            chatItem.classList.add('active');
            loadChat(chat.id);
        };
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
    // Remove 'active' class from all chat items
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
    // Add 'active' class to the selected chat item
    const selectedChat = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
    if (selectedChat) {
        selectedChat.classList.add('active');
    }
    
    currentChatId = chatId;
    clearMessages();
    
    // Load chat messages only from the chat's messages array
    const chat = chats.find(c => c.id === chatId);
    if (chat && chat.messages) {
        chat.messages.forEach(msg => {
            addMessage(msg.content, msg.isUser, false); // Added false parameter to prevent re-adding to history
        });
    }
}

function addMessage(message, isUser, saveToHistory = true) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (!isUser) {
        // Split message into paragraphs
        const paragraphs = message.split('\n\n');
        const formattedParagraphs = paragraphs.map(paragraph => {
            // Check if paragraph contains numbered list items
            if (paragraph.match(/^\d+\./m)) {  // Check if any line starts with number and period
                // Split into lines and filter empty ones
                const lines = paragraph.split('\n').filter(line => line.trim());
                // Check if these are actually numbered list items
                if (lines.every(line => /^\d+\./.test(line.trim()))) {
                    return `<ol start="${lines[0].match(/^\d+/)[0]}">${
                        lines.map(line => {
                            // Extract the text after the number and period
                            const text = line.replace(/^\d+\.\s*/, '');
                            return `<li>${text}</li>`;
                        }).join('')
                    }</ol>`;
                }
            }
            // Check if paragraph is a bullet list
            else if (paragraph.includes('* ')) {
                const listItems = paragraph.split('* ').filter(item => item.trim());
                return `<ul>${listItems.map(item => `<li>${item.trim()}</li>`).join('')}</ul>`;
            }
            // Regular paragraph
            return `<p>${paragraph}</p>`;
        });
        
        messageDiv.innerHTML = formattedParagraphs.join('');
    } else {
        messageDiv.textContent = message;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Only save to chat history if saveToHistory is true
    if (saveToHistory && currentChatId) {
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
    
    // Add user message
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
                <span>.</span><span>.</span><span>.</span>
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
                chat_id: currentChatId,
                chat_history: chatHistory[currentChatId] || []
            })
        });
        
        const data = await response.json();
        
        // Add terminal messages if present
        if (data.debug_logs) {
            data.debug_logs.forEach(log => {
                addTerminalMessage(log.message, log.type, log.timestamp);
            });
        }
        
        // Remove typing indicator
        typingDiv.remove();
        
        // Add assistant's response
        addMessage(data.response, false);
        
        // Update chat history
        if (currentChatId) {
            if (!chatHistory[currentChatId]) {
                chatHistory[currentChatId] = [];
            }
            chatHistory[currentChatId].push(
                { content: message, isUser: true },
                { content: data.response, isUser: false }
            );
        }
        
    } catch (error) {
        addTerminalMessage(error.message, 'error');
        typingDiv.remove();
        addMessage('Error: Could not get response', false);
    }
}

// Configuration update function
async function updateConfig() {
    const retainMode = document.getElementById('retainMode').checked;
    const checkBeforeLLM = document.getElementById('checkBeforeLLM').checked;
    const similarityThreshold = parseFloat(document.getElementById('similarity-threshold').value);
    const modelName = document.getElementById('modelName').value;

    const config = {
        retain_mode: retainMode,
        check_before_llm: checkBeforeLLM,
        similarity_threshold: similarityThreshold,
        model_name: modelName
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
            updateSettingsVisibility();
            showToast('Settings updated successfully', 'success');
        } else {
            throw new Error('Failed to update config');
        }
    } catch (error) {
        console.error('Error updating config:', error);
        showToast('Failed to update settings', 'error');
    }
}

// Add event listeners
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
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

// Add to your existing JavaScript
function updateSettingsVisibility() {
    const retainMode = document.getElementById('retainMode').checked;
    const similarityThresholdSetting = document.getElementById('similarityThresholdSetting');
    
    if (retainMode) {
        // In retain mode, only hide threshold, don't affect check before LLM
        similarityThresholdSetting.style.display = 'none';
    } else {
        // In normal mode, show threshold
        similarityThresholdSetting.style.display = 'block';
    }
}

// Add event listeners
document.getElementById('retainMode').addEventListener('change', updateSettingsVisibility);

// Initialize settings visibility on page load
document.addEventListener('DOMContentLoaded', () => {
    // Load initial settings from server
    fetch('/get-config')
        .then(response => response.json())
        .then(config => {
            document.getElementById('retainMode').checked = config.retain_mode;
            document.getElementById('checkBeforeLLM').checked = config.check_before_llm;
            document.getElementById('similarity-threshold').value = config.similarity_threshold;
            document.getElementById('similarity-value').textContent = config.similarity_threshold;
            document.getElementById('modelName').value = config.model_name;
            updateSettingsVisibility();
        });
});

// Add this to your existing JavaScript
function initializeSidebarToggle() {
    const appContainer = document.querySelector('.app-container');
    const toggleButton = document.getElementById('sidebarToggle');
    
    toggleButton.addEventListener('click', () => {
        appContainer.classList.toggle('sidebar-collapsed');
        
        // Store the state in localStorage
        const isCollapsed = appContainer.classList.contains('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    });
    
    // Restore sidebar state on page load
    const wasCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (wasCollapsed) {
        appContainer.classList.add('sidebar-collapsed');
    }
}

// Add this to your DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', () => {
    initializeSidebarToggle();
    // ... your existing initialization code ...
});

// Terminal handling
let isTerminalOpen = false;

function toggleTerminal() {
    const appContainer = document.querySelector('.app-container');
    isTerminalOpen = !isTerminalOpen;
    
    if (isTerminalOpen) {
        appContainer.classList.add('terminal-active');
        // Auto-collapse sidebar when terminal opens
        appContainer.classList.add('sidebar-collapsed');
    } else {
        appContainer.classList.remove('terminal-active');
    }
    
    // Store terminal state
    localStorage.setItem('terminalOpen', isTerminalOpen);
}

function addTerminalMessage(message, type = 'info', timestamp = null) {
    const terminal = document.getElementById('terminalContent');
    const msgElement = document.createElement('div');
    msgElement.className = `terminal-msg terminal-${type}`;
    
    // Format timestamp if provided
    const timeStr = timestamp ? `[${timestamp}] ` : '';
    const typeStr = type.toUpperCase();
    
    msgElement.innerHTML = `<span class="terminal-timestamp">${timeStr}</span><span class="terminal-type">[${typeStr}]</span> ${message}`;
    terminal.appendChild(msgElement);
    terminal.scrollTop = terminal.scrollHeight;
}

// Initialize terminal state on page load
document.addEventListener('DOMContentLoaded', () => {
    const wasTerminalOpen = localStorage.getItem('terminalOpen') === 'true';
    if (wasTerminalOpen) {
        toggleTerminal();
    }
});

function clearTerminal() {
    const terminal = document.getElementById('terminalContent');
    terminal.innerHTML = '';
    // Add a cleared message
    addTerminalMessage('Terminal cleared', 'info');
}

// Find the slider element and value display
const similaritySlider = document.getElementById('similarity-threshold');
const similarityValue = document.getElementById('similarity-value');

// When the page loads, fetch the config value and set both slider and display
fetch('/get_config')
    .then(response => response.json())
    .then(config => {
        similaritySlider.value = config.similarity_threshold;
        similarityValue.textContent = config.similarity_threshold;
    });

// Update the display value when slider moves
similaritySlider.addEventListener('input', function() {
    similarityValue.textContent = this.value;
});