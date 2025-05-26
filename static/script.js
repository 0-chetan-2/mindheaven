// Fixed script.js with comprehensive safeguards against infinite loops
const chatForm = document.getElementById('chat-form');
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const moodBadge = document.getElementById('mood-badge');
const moodExplanationText = document.getElementById('mood-explanation-text');
const clearChatButton = document.getElementById('clear-chat');
const sendButton = chatForm ? chatForm.querySelector('button[type="submit"]') : null;

// CRITICAL: Single instance state tracking
let isSubmitting = false;
let chartInitialized = false;
let hasFetchedMoodHistory = false;
let lastUpdateTime = 0; // Timestamp of last chart update
const UPDATE_THRESHOLD = 1000; // Minimum milliseconds between updates
const messageSendDelay = 1000; // 1 second between messages

// Color mapping for different moods
const moodColors = {
    'positive': '#4CAF50',
    'negative': '#F44336',
    'neutral': '#9E9E9E',
    'anxious': '#FFC107',
    'depressed': '#673AB7',
    'happy': '#2196F3',
    'angry': '#FF5722',
    'confused': '#607D8B'
};

// Initialize mood chart - Only create once
let moodChart = null;
function initMoodChart() {
    // CRITICAL: Stop multiple initializations
    if (chartInitialized || moodChart !== null) return;
    
    const ctx = document.getElementById('mood-chart');
    if (!ctx) return;
    
    try {
        // Destroy existing chart if one exists (should never happen due to checks above)
        if (moodChart) {
            moodChart.destroy();
        }
        
        moodChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Mood Intensity',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }]
            },
            options: {
                animation: {
                    duration: 0 // Disable animations to prevent continuous redraws
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 10,
                        min: 0,
                        title: {
                            display: true,
                            text: 'Intensity (1-10)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Message'
                        }
                    }
                },
                responsive: true,
                maintainAspectRatio: true // CHANGED: This helps prevent expansion
            }
        });
        
        chartInitialized = true;
        console.log("Chart initialized successfully");
    } catch (error) {
        console.error("Failed to initialize chart:", error);
    }
}

// Function to update mood chart with new data - with throttling
function updateMoodChart(mood, intensity) {
    // CRITICAL: Throttle updates to prevent rapid successive calls
    const now = Date.now();
    if (now - lastUpdateTime < UPDATE_THRESHOLD) {
        console.log("Update throttled - too soon since last update");
        return;
    }
    lastUpdateTime = now;
    
    if (!chartInitialized) {
        initMoodChart();
    }
    
    if (!moodChart) {
        console.warn("Chart not available for update");
        return;
    }
    
    // Safety check on intensity
    if (typeof intensity !== 'number') {
        console.warn('Intensity is not a number:', intensity);
        intensity = 5; // Default fallback
    }
    
    // Constrain to valid range
    intensity = Math.max(0, Math.min(10, intensity));
    
    // Only keep the last 10 entries
    if (moodChart.data.labels.length >= 10) {
        moodChart.data.labels.shift();
        moodChart.data.datasets[0].data.shift();
    }
    
    // Add new data point
    const messageNum = moodChart.data.labels.length + 1;
    moodChart.data.labels.push(`Msg ${messageNum}`);
    moodChart.data.datasets[0].data.push(intensity);
    
    // Update chart colors
    moodChart.data.datasets[0].borderColor = moodColors[mood] || 'rgb(75, 192, 192)';
    
    // Update with animation disabled for this update
    moodChart.update();
    
    // Show the chart container if it was hidden
    const moodHistoryContainer = document.getElementById('mood-history-container');
    if (moodHistoryContainer && moodHistoryContainer.classList.contains('mood-history-hidden')) {
        moodHistoryContainer.classList.remove('mood-history-hidden');
    }
    
    console.log(`Chart updated: ${mood} (${intensity})`);
}

// Update the mood indicator
function updateMoodIndicator(mood, intensity) {
    if (!moodBadge) return;
    moodBadge.textContent = `${mood.charAt(0).toUpperCase() + mood.slice(1)} (${intensity}/10)`;
    moodBadge.style.backgroundColor = moodColors[mood] || '#9E9E9E';
    moodBadge.style.color = ['positive', 'happy', 'neutral'].includes(mood) ? '#000' : '#fff';
}

function appendMessage(sender, text, isCrisis = false) {
    if (!chatBox) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    
    if (isCrisis) {
        messageDiv.classList.add('crisis-message');
    }
    
    const senderLabel = sender === 'user' ? 'You' : 'MindHeaven';
    
    let formattedText = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    
    messageDiv.innerHTML = `<span class="sender-label">${senderLabel}:</span> ${formattedText}`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Fetch mood history with multiple safeguards
async function fetchMoodHistory() {
    // CRITICAL: Stop multiple fetches
    if (hasFetchedMoodHistory) {
        console.log("Already fetching mood history, request ignored");
        return;
    }
    
    hasFetchedMoodHistory = true;
    console.log("Fetching mood history...");
    
    try {
        const response = await fetch('/mood_history');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.moods && Array.isArray(data.moods) && data.moods.length > 0) {
            // Initialize chart if needed
            if (!chartInitialized) {
                initMoodChart();
            }
            
            if (!moodChart) {
                console.warn("Chart not available after initialization");
                return;
            }
            
            // Clear existing data (defensive clearing)
            moodChart.data.labels = [];
            moodChart.data.datasets[0].data = [];
            
            // Add each mood entry (last 10 only)
            const moods = data.moods.slice(-10);
            moods.forEach((entry, index) => {
                moodChart.data.labels.push(`Msg ${index + 1}`);
                
                // Ensure valid numeric intensity
                let intensity = 5;
                if (typeof entry.intensity === 'number') {
                    intensity = Math.max(0, Math.min(10, entry.intensity));
                }
                
                moodChart.data.datasets[0].data.push(intensity);
            });
            
            // Update the chart with animation disabled
            moodChart.update();
            
            // Show the chart container
            const moodHistoryContainer = document.getElementById('mood-history-container');
            if (moodHistoryContainer) {
                moodHistoryContainer.classList.remove('mood-history-hidden');
            }
            
            // Update mood indicator with latest mood
            if (moods.length > 0) {
                const latestMood = moods[moods.length - 1];
                updateMoodIndicator(latestMood.mood, latestMood.intensity);
            }
            
            console.log(`Loaded ${moods.length} mood history entries`);
        } else {
            // Hide chart if no mood data
            const moodHistoryContainer = document.getElementById('mood-history-container');
            if (moodHistoryContainer) {
                moodHistoryContainer.classList.add('mood-history-hidden');
            }
            console.log("No mood history available");
        }
    } catch (error) {
        console.error('Error fetching mood history:', error);
    } finally {
        // Reset flag after delay
        setTimeout(() => {
            hasFetchedMoodHistory = false;
            console.log("Mood history fetch flag reset");
        }, 10000);
    }
}

// Clear conversation handling
if (clearChatButton) {
    // CRITICAL: Only add listener once
    clearChatButton.removeEventListener('click', clearConversation);
    clearChatButton.addEventListener('click', clearConversation);
}

// Separate function for clearing to avoid duplicate handlers
async function clearConversation() {
    if (isSubmitting) return;
    isSubmitting = true;
    
    if (sendButton) sendButton.disabled = true;
    if (userInput) userInput.disabled = true;
    
    try {
        const response = await fetch('/clear_conversation', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Clear chat display
        if (chatBox) chatBox.innerHTML = '';
        
        // Reset mood indicator
        if (moodBadge) {
            moodBadge.textContent = 'Analyzing...';
            moodBadge.style.backgroundColor = '#9E9E9E';
        }
        
        if (moodExplanationText) {
            moodExplanationText.textContent = 'Share how you\'re feeling to get insights.';
        }
        
        // Reset chart data
        if (moodChart) {
            moodChart.data.labels = [];
            moodChart.data.datasets[0].data = [];
            moodChart.update();
        }
        
        // Hide chart
        const moodHistoryContainer = document.getElementById('mood-history-container');
        if (moodHistoryContainer) {
            moodHistoryContainer.classList.add('mood-history-hidden');
        }
        
        // Add welcome message
        appendMessage('assistant', 'Hello! I\'m here to listen and support you. How are you feeling today?');
    } catch (error) {
        console.error('Error clearing conversation:', error);
    } finally {
        setTimeout(() => {
            isSubmitting = false;
            if (sendButton) sendButton.disabled = false;
            if (userInput) userInput.disabled = false;
        }, 500);
    }
}

// Send message handling
if (chatForm) {
    // CRITICAL: Remove existing handlers to prevent stacking
    chatForm.removeEventListener('submit', submitMessage);
    chatForm.addEventListener('submit', submitMessage);
}

// Separate function for message submission
async function submitMessage(e) {
    e.preventDefault();
    
    // Prevent multiple submissions
    if (isSubmitting) {
        console.log("Submission in progress, ignoring duplicate");
        return;
    }
    isSubmitting = true;
    
    if (sendButton) sendButton.disabled = true;
    if (userInput) userInput.disabled = true;
    
    const message = userInput.value.trim();
    if (!message) {
        isSubmitting = false;
        if (sendButton) sendButton.disabled = false;
        if (userInput) userInput.disabled = false;
        return;
    }
    
    appendMessage('user', message);
    userInput.value = '';
    
    // Show typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.classList.add('typing-indicator');
    typingIndicator.textContent = 'MindHeaven is typing...';
    chatBox.appendChild(typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        // Remove typing indicator
        if (typingIndicator.parentNode) {
            chatBox.removeChild(typingIndicator);
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add bot response
        appendMessage('assistant', data.reply, data.is_crisis);
        
        // Update mood information safely
        if (data.mood_analysis) {
            updateMoodIndicator(data.mood_analysis.mood, data.mood_analysis.intensity);
            
            // Throttled chart update
            setTimeout(() => {
                updateMoodChart(data.mood_analysis.mood, data.mood_analysis.intensity);
            }, 100);
            
            // Update explanation text
            if (data.mood_analysis.explanation && moodExplanationText) {
                moodExplanationText.textContent = data.mood_analysis.explanation;
            }
            
            // Handle crisis resources
            const resourcesElement = document.getElementById('resources');
            if (data.is_crisis && resourcesElement) {
                resourcesElement.classList.add('highlight-resources');
            } else if (resourcesElement) {
                resourcesElement.classList.remove('highlight-resources');
            }
        }
    } catch (error) {
        // Remove typing indicator
        if (typingIndicator.parentNode) {
            chatBox.removeChild(typingIndicator);
        }
        
        appendMessage('assistant', 'Sorry, something went wrong. Please try again.');
        console.error('Error sending message:', error);
    } finally {
        // Delay re-enabling input
        setTimeout(() => {
            isSubmitting = false;
            if (sendButton) sendButton.disabled = false;
            if (userInput) userInput.disabled = false;
            if (userInput) userInput.focus();
        }, messageSendDelay);
    }
}

// On page load - with safeguards against multiple initializations
let hasInitialized = false;
window.addEventListener('DOMContentLoaded', () => {
    if (hasInitialized) {
        console.log("Already initialized, preventing duplicate initialization");
        return;
    }
    hasInitialized = true;
    
    console.log("DOM loaded, initializing chat interface...");
    
    // Initialize chart (hidden until data arrives)
    try {
        initMoodChart();
    } catch (error) {
        console.error('Error initializing chart:', error);
    }
    
    // Fetch mood history
    try {
        fetchMoodHistory();
    } catch (error) {
        console.error('Error fetching mood history:', error);
    }
    
    // Add welcome message if chatbox is empty
    try {
        if (chatBox && chatBox.children.length === 0) {
            appendMessage('assistant', 'Hello! I\'m here to listen and support you. How are you feeling today?');
        }
    } catch (error) {
        console.error('Error adding welcome message:', error);
    }
});

// CRITICAL: Prevent duplicate event listener stacking on window events
function windowLoadHandler() {
    console.log("Window fully loaded");
    
    // Add class to mood history container if needed
    const moodHistoryContainer = document.getElementById('mood-history-container');
    if (moodHistoryContainer && !moodHistoryContainer.classList.contains('mood-history-hidden')) {
        moodHistoryContainer.classList.add('mood-history-hidden');
    }
}

window.removeEventListener('load', windowLoadHandler);
window.addEventListener('load', windowLoadHandler);