# MindHeaven: Mental Health Support Chatbot

MindHeaven is a supportive, AI-powered mental health chatbot designed to provide a safe space for users to share their thoughts and feelings. The chatbot offers empathetic, non-judgmental conversation, mood tracking, and quick access to crisis resources, with a special focus on users in India.

## Features

- **Conversational Support:** Uses OpenAI's GPT model to provide empathetic, context-aware responses.
- **Crisis Detection:** Automatically detects crisis or self-harm language and provides immediate helpline information.
- **Indian Helplines:** Shares up-to-date Indian mental health and emergency contact details.
- **Mood Tracking:** Analyzes and visualizes user mood trends over time.
- **Session History:** Remembers recent conversations for a more personalized experience.
- **Rate Limiting & Security:** Protects user privacy and prevents abuse.

## Technologies Used

- Python, Flask, Flask-Session, Flask-Limiter, Flask-CORS
- OpenAI GPT-3.5 Turbo API
- HTML, CSS, JavaScript (frontend)
- Chart.js for mood visualization

## Getting Started

1. **Clone the repository.**
2. **Install dependencies** from `requirements.txt`:
   ```
   pip install -r requirements.txt
   ```
3. **Set your OpenAI API key** in a `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. **Run the Flask app**:
   ```
   python app.py
   ```
5. **Open your browser** and go to `http://localhost:5000`

## Disclaimer

MindHeaven is **not a substitute for professional mental health care**. If you or someone you know is in crisis, please use the provided helplines or contact emergency services.