# EchoVerse Backend

A Python Flask backend for the EchoVerse AI-powered audiobook creation tool.

## Features

- **Tone-Adaptive Text Rewriting**: Uses IBM Watsonx LLM to rewrite text in various emotional tones
- **High-Quality Voice Narration**: Converts text to speech using IBM Watson TTS
- **Multiple Voice Options**: Lisa, Michael, and Allison voices available
- **9 Emotional Tones**: Neutral, Suspenseful, Inspiring, Cheerful, Sad, Angry, Playful, Calm, Confident
- **RESTful API**: Clean endpoints for frontend integration
- **Error Handling**: Comprehensive error handling and logging
- **Health Monitoring**: Health check endpoint for service status

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python init_db.py
```

This will create the SQLite database with all necessary tables and sample data.

### 3. Configure IBM Cloud Services

1. Create an IBM Cloud account
2. Set up Watsonx (LLM) service
3. Set up Watson Text-to-Speech service
4. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your IBM Cloud credentials:
```
WATSONX_API_KEY=your_watsonx_api_key_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your_project_id_here
TTS_API_KEY=your_tts_api_key_here
TTS_URL=https://api.us-south.text-to-speech.watson.cloud.ibm.com
```

### 4. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

## Database Schema

The application uses SQLite for development with the following tables:

### Core Tables
- **users** - Student/user profiles
- **audio_history** - Text processing and audio generation history
- **tones** - Available emotional tones
- **voices** - Available voice options

### Related Tables
- **user_skills** - User technical skills
- **user_interests** - User interests
- **user_achievements** - User achievements
- **user_projects** - User projects

## API Endpoints

### Health Check
- **GET** `/health` - Check service status

### Text Rewriting
- **POST** `/rewrite`
  ```json
  {
    "text": "Your text here",
    "tone": "cheerful",
    "user_email": "user@example.com"
  }
  ```

### Text-to-Speech
- **POST** `/synthesize`
  ```json
  {
    "text": "Text to convert to audio",
    "voice": "lisa",
    "history_id": 123
  }
  ```

### User Management
- **POST** `/users` - Create new user
- **GET** `/users/<email>` - Get user profile
- **PUT** `/users/<email>` - Update user profile

### History Management
- **GET** `/users/<email>/history` - Get user's audio history
- **DELETE** `/history/<id>` - Delete history item

### Configuration
- **GET** `/voices` - List available voices
- **GET** `/tones` - List available tones

## Available Tones

- `neutral` - Clear and balanced narration
- `suspenseful` - Dramatic and engaging delivery
- `inspiring` - Uplifting and motivational tone
- `cheerful` - Bright, happy, and energetic
- `sad` - Soft, somber, and emotional
- `angry` - Intense and passionate delivery
- `playful` - Fun, lively, and whimsical
- `calm` - Relaxed and soothing narration
- `confident` - Assured and persuasive

## Available Voices

- `lisa` - Warm and professional female voice
- `michael` - Confident and clear male voice
- `allison` - Friendly and expressive female voice

## Testing

You can test the API endpoints using curl:

```bash
# Health check
curl http://localhost:5000/health

# Rewrite text
curl -X POST http://localhost:5000/rewrite \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "tone": "cheerful"}'

# Get voices
curl http://localhost:5000/voices
```

## Production Deployment

For production deployment, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```
