import os
import json
import logging
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from flask_session import Session
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging.handlers
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client with the new API structure
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Rotating file handler
handler = logging.handlers.RotatingFileHandler(
    'app.log',
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5
)
logger.addHandler(handler)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
Session(app)

# Crisis keywords for detection
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "harm myself",
    "self-harm", "cut myself", "hurting myself", "don't want to live",
    "better off dead", "no reason to live", "how to die", "end it all", "take my own life",
    "giving up", "can't go on", "don't know what to do anymore", "no way out",
    "overwhelmed", "i can't take it anymore", "i feel trapped", "i want to disappear",
    "i'm done with everything", "i can't do this anymore", "i feel hopeless", "i feel helpless",
    "i want to give up", "i'm at my limit", "i can't handle this", "i want it to stop",
    "i wish i was dead", "i wish i could just disappear"
]

# Pattern matching for common inputs
COMMON_PATTERNS = {
    r"\b(hi|hello|hey|greetings)\b": {
        "responses": [
            "Hello! How are you feeling today?",
            "Hi there! I'm here to chat with you. How are you doing?",
            "Hey! It's nice to hear from you. How's your day going?"
        ],
        "mood": "neutral",
        "intensity": 5
    },
    r"\b(good|great|fine|okay|happy|excellent)\b": {
        "responses": [
            "I'm glad to hear you're doing well! Is there anything specific you'd like to talk about?",
            "That's wonderful! What's been going well for you lately?",
            "Great to hear that! What's made your day positive so far?"
        ],
        "mood": "positive",
        "intensity": 7
    },
    r"\b(sad|down|depressed|unhappy|upset|blue)\b": {
        "responses": [
            "I'm sorry to hear you're feeling down. Would you like to talk about what's troubling you?",
            "It can be tough to feel that way. What's been on your mind lately?",
            "I'm here to listen if you want to share more about what's making you feel this way."
        ],
        "mood": "depressed",
        "intensity": 6
    },
    r"\b(angry|mad|frustrated|annoyed)\b": {
        "responses": [
            "I understand feeling frustrated. What's causing these feelings?",
            "It sounds like you're dealing with some strong emotions. Would you like to talk about what happened?",
            "Being angry is a natural response sometimes. What's been frustrating you?"
        ],
        "mood": "angry",
        "intensity": 6
    },
    r"\b(anxious|worried|nervous|stressed|fear|scary)\b": {
        "responses": [
            "Anxiety can be really challenging. What's making you feel anxious right now?",
            "I understand that worry can be overwhelming. What's on your mind?",
            "Feeling stressed is common. Can you share what's causing this feeling?"
        ],
        "mood": "anxious",
        "intensity": 6
    },
    r"\b(tired|exhausted|sleepy|fatigued)\b": {
        "responses": [
            "Being tired can really affect how we feel. Have you been able to get enough rest?",
            "Fatigue can be difficult to deal with. What's your sleep been like lately?",
            "Taking care of your energy levels is important. What might help you recharge?"
        ],
        "mood": "negative",
        "intensity": 4
    },
    r"\b(thank you|thanks)\b": {
        "responses": [
            "You're welcome! I'm here to support you.",
            "Glad I could help! Is there anything else you'd like to discuss?",
            "Of course! I'm here whenever you need to talk."
        ],
        "mood": "positive",
        "intensity": 6
    },
    r"\b(bye|goodbye|see you|talk later)\b": {
        "responses": [
            "Take care of yourself! Feel free to come back anytime.",
            "Goodbye for now. I'll be here when you want to chat again.",
            "Take care! Remember to be kind to yourself."
        ],
        "mood": "neutral",
        "intensity": 5
    },
    # Generic fallback when no pattern matches
    "default": {
        "responses": [
            "I'm listening. Can you tell me more?",
            "I'm here to support you. Would you like to share more about what's on your mind?",
            "Thank you for sharing. How does that make you feel?",
            "I see. What else would you like to talk about today?",
            "I appreciate you opening up. Is there anything specific you'd like to discuss?"
        ],
        "mood": "neutral",
        "intensity": 5
    }
}

# Additional emotional patterns
EMOTIONAL_PATTERNS = {
    r"\b(love|loved|loving)\b": {
        "responses": [
            "Love is such a powerful emotion. Can you tell me more about these feelings?",
            "It sounds like this is meaningful to you. What about it stands out?",
            "Those feelings can be really important. How does it affect you?"
        ],
        "mood": "positive",
        "intensity": 8
    },
    r"\b(hopeless|helpless|worthless)\b": {
        "responses": [
            "I'm really sorry you're feeling this way. These feelings can be overwhelming but they're not permanent. What's contributing to this feeling?",
            "That's a really difficult feeling to experience. Would you like to talk more about what's going on?",
            "Those feelings are really challenging. Please know you're not alone in this. What's been happening recently?"
        ],
        "mood": "depressed",
        "intensity": 8
    },
    r"\b(lonely|alone|isolated)\b": {
        "responses": [
            "Feeling lonely can be really difficult. Would you like to talk about what's making you feel isolated?",
            "I'm sorry you're feeling alone. Social connection is so important. What's been happening with your relationships lately?",
            "That sounds really hard. Loneliness affects many people. What might help you feel more connected?"
        ],
        "mood": "depressed",
        "intensity": 7
    },
    r"\b(confused|unsure|uncertain|don't know)\b": {
        "responses": [
            "It's okay to feel uncertain sometimes. What specifically are you feeling confused about?",
            "Confusion and uncertainty can be uncomfortable. What would help bring some clarity?",
            "Taking time to process complex situations is important. What's making you feel uncertain?"
        ],
        "mood": "confused",
        "intensity": 5
    },
    r"\b(excited|thrilled|eager)\b": {
        "responses": [
            "That sounds wonderful! What's making you feel excited?",
            "It's great to hear you're feeling enthusiastic! What are you looking forward to?",
            "Excitement is such a positive energy! Tell me more about what's got you feeling this way."
        ],
        "mood": "happy",
        "intensity": 8
    }
}

# Crisis response messages
CRISIS_RESPONSES = [
    "I'm concerned about what you're sharing. If you're in immediate danger, please contact emergency services (112 in India) or a crisis helpline like the Snehi Suicide Prevention Helpline (91-22-2772 6771/6773). Would it help to talk more about what you're experiencing?",
    "It sounds like you're going through a really difficult time. Your safety is important - please consider reaching out to a crisis counselor by calling the Snehi Suicide Prevention Helpline (91-22-2772 6771/6773) or the iCALL helpline (9152987821). Would you like to tell me more about what's happening?",
    "I'm really concerned about you right now. Please consider talking to a mental health professional as soon as possible. The Snehi Suicide Prevention Helpline (91-22-2772 6771/6773), iCALL (9152987821), and the Kiran Mental Health Rehabilitation Helpline (1800-599-0019) are available. Can we continue talking about what's bringing up these feelings?"
]

# Merge all patterns
ALL_PATTERNS = {**COMMON_PATTERNS, **EMOTIONAL_PATTERNS}

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

def get_response(message):
    """
    Generate a response using OpenAI API.
    
    Args:
        message (str): User's input message
        
    Returns:
        dict: Response containing reply, mood analysis, and crisis flag
    """
    message_lower = message.lower()
    
    # Check for crisis keywords first
    if detect_crisis(message_lower) or openai_crisis_check(message):
        return {
            "reply": random.choice(CRISIS_RESPONSES),
            "mood_analysis": {
                "mood": "depressed",
                "intensity": 8,
                "explanation": "The message contains concerning language that may indicate a crisis."
            },
            "is_crisis": True
        }
    
    try:
        # Create a conversation context
        conversation = [
            {"role": "system", "content": "You are a supportive and empathetic mental health chatbot. Your responses should be helpful, understanding, and focused on providing emotional support. Keep responses concise and natural."},
            {"role": "user", "content": message}
        ]
        
        # Get response from OpenAI using the new API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation,
            max_tokens=150,
            temperature=0.7
        )
        
        # Extract the response text
        reply = response.choices[0].message.content
        
        # Analyze mood using OpenAI
        mood_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Analyze the emotional tone of the following message and respond with a JSON object containing 'mood' (one of: positive, negative, neutral, anxious, depressed, angry), 'intensity' (1-10), and 'explanation'."},
                {"role": "user", "content": message}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        # Parse mood analysis
        try:
            mood_data = json.loads(mood_response.choices[0].message.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            mood_data = {
                "mood": "neutral",
                "intensity": 5,
                "explanation": "Unable to parse mood analysis from AI response."
            }
        
        return {
            "reply": reply,
            "mood_analysis": mood_data,
            "is_crisis": False
        }
        
    except Exception as e:
        logger.error(f"Error in OpenAI API call: {str(e)}")
        # Fallback to pattern matching if API call fails
        for pattern, data in ALL_PATTERNS.items():
            if pattern != "default" and re.search(pattern, message_lower):
                return {
                    "reply": random.choice(data["responses"]),
                    "mood_analysis": {
                        "mood": data["mood"],
                        "intensity": data["intensity"],
                        "explanation": f"Message contains words suggesting a {data['mood']} mood."
                    },
                    "is_crisis": False
                }
        
        return {
            "reply": random.choice(ALL_PATTERNS["default"]["responses"]),
            "mood_analysis": {
                "mood": "neutral",
                "intensity": 5,
                "explanation": "Unable to determine specific mood from the message."
            },
            "is_crisis": False
        }

def openai_crisis_check(message):
    """Check if message indicates crisis using OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a mental health assistant. If the following message indicates a crisis or risk of self-harm or suicide, respond with 'true'. Otherwise, respond with 'false'."},
                {"role": "user", "content": message}
            ],
            max_tokens=5,
            temperature=0
        )
        result = response.choices[0].message.content.strip().lower()
        return result == "true"
    except Exception as e:
        logger.error(f"OpenAI crisis check failed: {e}")
        return False

def detect_crisis(text):
    """Function to detect crisis indicators in a message"""
    text_lower = text.lower() if isinstance(text, str) else ""
    for keyword in CRISIS_KEYWORDS:
        if keyword in text_lower:
            return True
    return False

# Route to serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle chat messages
@app.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        user_msg = data.get('message', '').strip()
        
        if not user_msg:
            return jsonify({"reply": "Please say something!"})

        # Initialize session data if needed
        if 'history' not in session:
            session['history'] = []
        if 'mood_history' not in session:
            session['mood_history'] = []
        
        # Limit session history size to prevent unbounded growth
        if len(session['history']) > 50:
            session['history'] = session['history'][-50:]
        if len(session['mood_history']) > 50:
            session['mood_history'] = session['mood_history'][-50:]
        
        # Add user message to history
        session['history'].append({"role": "user", "content": user_msg})
        
        # Generate response
        response_data = get_response(user_msg)
        
        # Add response to history
        session['history'].append({"role": "assistant", "content": response_data["reply"]})
        
        # Add mood to history
        session['mood_history'].append({
            "timestamp": datetime.now().isoformat(),
            "message": user_msg,
            "mood": response_data["mood_analysis"]["mood"],
            "intensity": response_data["mood_analysis"]["intensity"]
        })
        
        # Save session
        session.modified = True
        
        # Return the response
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": "An error occurred processing your message"}), 500

# Route to get mood history
@app.route('/mood_history', methods=['GET'])
def get_mood_history():
    if 'mood_history' not in session:
        return jsonify({"moods": []})
    
    # Limit returned moods to prevent large responses
    moods = session['mood_history'][-20:] if len(session['mood_history']) > 20 else session['mood_history']
    return jsonify({"moods": moods})

# Route to clear conversation
@app.route('/clear_conversation', methods=['POST'])
def clear_conversation():
    session['history'] = []
    # Keep mood_history for continuity in tracking
    session.modified = True
    return jsonify({"status": "success"})

# Route for getting resources
@app.route('/resources', methods=['GET'])
def get_resources():
    resources = {
        "crisis": [
            {
                "name": "Snehi Suicide Prevention Helpline",
                "description": "Call 91-22-2772 6771/6773",
                "url": "https://www.snehi.org/"
            },
            {
                "name": "iCALL Helpline",
                "description": "Call 9152987821",
                "url": "https://icallhelpline.org/"
            },
            {
                "name": "Kiran Mental Health Rehabilitation Helpline",
                "description": "Call 1800-599-0019",
                "url": "https://www.mhrdnats.gov.in/"
            },
            {
                "name": "Emergency Services (India)",
                "description": "Call 112 for immediate assistance",
                "url": "https://112.gov.in/"
            }
        ],
        "general": [
            {
                "name": "Vandrevala Foundation",
                "description": "Call 9999666555 or 1860-2662-345",
                "url": "https://www.vandrevalafoundation.com/"
            },
            {
                "name": "Fortis Stress Helpline",
                "description": "Call 08376804102",
                "url": "https://www.fortishealthcare.com/india/mental-health-and-behavioural-sciences"
            }
        ]
    }
    return jsonify(resources)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "The requested resource was not found"}), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {str(e)}", exc_info=True)
    return jsonify({"error": "An internal server error occurred"}), 500

@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)