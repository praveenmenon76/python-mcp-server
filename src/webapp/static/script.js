// Script for the MCP Chat Interface

document.addEventListener('DOMContentLoaded', function() {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const toolsList = document.getElementById('tools-list');

    // Load available tools
    fetchTools();

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Focus on input when page loads
    userInput.focus();

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
        
        // Clear input
        userInput.value = '';
        
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
        })
        .catch(error => {
            // Remove loading indicator
            hideLoading(loadingId);
            
            console.error('Error:', error);
            addMessage('An error occurred while processing your request.', 'system');
            
            // Scroll to bottom
            scrollToBottom();
        });
    }

    // Function to add a message to the chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        // Format text with line breaks
        const formattedText = formatMessage(text);
        messageDiv.innerHTML = formattedText;
        
        chatWindow.appendChild(messageDiv);
        scrollToBottom();
    }
    
    // Function to format messages with proper HTML
    function formatMessage(text) {
        // Replace newlines with <br>
        let formatted = text.replace(/\n/g, '<br>');
        
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
        loadingDiv.innerHTML = 'Thinking<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>';
        
        chatWindow.appendChild(loadingDiv);
        scrollToBottom();
        
        // Animate the dots
        const dots = loadingDiv.querySelectorAll('.dot');
        let i = 0;
        
        const intervalId = setInterval(() => {
            dots.forEach((dot, index) => {
                dot.style.opacity = index === i % 3 ? 1 : 0.3;
            });
            i++;
        }, 300);
        
        // Return an object with references to remove the loading indicator later
        return {
            element: loadingDiv,
            intervalId: intervalId
        };
    }

    // Function to hide loading indicator
    function hideLoading(loading) {
        clearInterval(loading.intervalId);
        loading.element.remove();
    }

    // Function to scroll to the bottom of the chat
    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
});