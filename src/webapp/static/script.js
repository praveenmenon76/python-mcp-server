// Modern chat interface script
document.addEventListener('DOMContentLoaded', function() {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const toolsList = document.getElementById('tools-list');

    // Load available tools
    fetchTools();

    // Focus on input when page loads
    userInput.focus();

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', function(e) {
        // Send on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
        
        // Auto-resize textarea as user types
        setTimeout(() => {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 100) + 'px';
        }, 0);
    });

    // Function to fetch available tools
    function fetchTools() {
        fetch('/api/tools')
            .then(response => response.json())
            .then(tools => {
                toolsList.innerHTML = '';
                tools.forEach(tool => {
                    const li = document.createElement('li');
                    li.textContent = `${tool.name}: ${tool.description}`;
                    toolsList.appendChild(li);
                });
            })
            .catch(error => {
                console.error('Error fetching tools:', error);
                addMessage('System error: Unable to fetch available tools.', 'system');
            });
    }

    // Function to send a message
    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;

        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input and reset height
        userInput.value = '';
        userInput.style.height = 'auto';
        
        // Show loading indicator
        const loadingId = showLoading();
        
        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            hideLoading(loadingId);
            
            // Add bot response to chat
            const botResponse = data.response;
            addMessage(botResponse, 'bot');
            
            // Scroll to bottom
            scrollToBottom();
            
            // Focus back on input
            userInput.focus();
        })
        .catch(error => {
            // Remove loading indicator
            hideLoading(loadingId);
            
            console.error('Error:', error);
            addMessage('Sorry, I encountered an error while processing your request.', 'system');
            
            // Scroll to bottom
            scrollToBottom();
        });
    }

    // Function to add a message to the chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        // Format text with line breaks and code
        const formattedText = formatMessage(text);
        messageDiv.innerHTML = formattedText;
        
        chatWindow.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Function to format messages with proper HTML
    function formatMessage(text) {
        // Replace newlines with <br>
        let formatted = text.replace(/\n/g, '<br>');
        
        // Handle code blocks with ```
        formatted = formatted.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
        
        // Handle inline code with `
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Check if it contains a list-like structure and format it
        if (formatted.includes('- ')) {
            // Split by line breaks
            const lines = formatted.split('<br>');
            let inList = false;
            let result = '';
            
            for (const line of lines) {
                if (line.trim().startsWith('- ')) {
                    // Start list if not already in one
                    if (!inList) {
                        result += '<ul>';
                        inList = true;
                    }
                    // Add list item
                    result += `<li>${line.trim().substring(2)}</li>`;
                } else {
                    // End list if we were in one
                    if (inList) {
                        result += '</ul>';
                        inList = false;
                    }
                    // Add normal line
                    result += line + '<br>';
                }
            }
            
            // Close list if still open
            if (inList) {
                result += '</ul>';
            }
            
            formatted = result;
        }
        
        return formatted;
    }

    // Function to show loading indicator
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'bot', 'loading');
        
        // Create the dots for the loading animation
        loadingDiv.innerHTML = 'Thinking<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
        
        chatWindow.appendChild(loadingDiv);
        scrollToBottom();
        
        return loadingDiv;
    }

    // Function to hide loading indicator
    function hideLoading(loadingElement) {
        if (loadingElement && loadingElement.parentNode) {
            loadingElement.remove();
        }
    }

    // Function to scroll to the bottom of the chat
    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
});