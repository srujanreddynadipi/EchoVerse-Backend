from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import DetailedResponse
import requests
import tempfile
import os
import json
import logging
from datetime import datetime
from database_manager import DatabaseManager
from huggingface_service import hf_service
import PyPDF2
import docx
import re
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS for React frontend - temporarily allow all origins for testing
CORS(app)

# Configure Flask settings for file uploads
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size
app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.doc', '.docx', '.txt']
app.config['UPLOAD_PATH'] = 'temp'

# Initialize database manager
db_manager = DatabaseManager()

# --- IBM Watson Configuration ---
# Replace these with your actual IBM Cloud credentials
WATSONX_API_KEY = os.getenv('WATSONX_API_KEY', 'YOUR_WATSONX_API_KEY')
WATSONX_URL = os.getenv('WATSONX_URL', 'YOUR_WATSONX_URL') 
WATSONX_PROJECT_ID = os.getenv('WATSONX_PROJECT_ID', 'YOUR_PROJECT_ID')

TTS_API_KEY = os.getenv('TTS_API_KEY', 'YOUR_TTS_API_KEY')
TTS_URL = os.getenv('TTS_URL', 'YOUR_TTS_URL')

# Initialize Text-to-Speech
try:
    tts_authenticator = IAMAuthenticator(TTS_API_KEY)
    tts = TextToSpeechV1(authenticator=tts_authenticator)
    tts.set_service_url(TTS_URL)
    logger.info("Text-to-Speech service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize TTS service: {e}")
    tts = None

# Voice mapping for different voice options with latest high-quality voices
VOICE_MAPPING = {
    'david': 'en-US_MichaelV3Voice',    # High-quality neural voice
    'zira': 'en-US_AllisonV3Voice',     # High-quality neural voice
    'heera': 'en-US_EmilyV3Voice',      # High-quality neural voice
    'mark': 'en-US_HenryV3Voice',       # High-quality neural voice
    'ravi': 'en-US_KevinV3Voice',       # High-quality neural voice
    # Legacy support for backward compatibility
    'lisa': 'en-US_AllisonV3Voice',
    'michael': 'en-US_MichaelV3Voice', 
    'allison': 'en-US_EmilyV3Voice'
}

# Load tone prompts from database
def get_tone_prompts():
    """Get tone prompts from database"""
    try:
        tones = db_manager.get_tones()
        return {tone['tone_id']: tone['prompt_template'] for tone in tones}
    except Exception as e:
        logger.error(f"Failed to load tones from database: {e}")
        # Fallback to hardcoded prompts
        return {
            'neutral': "Rewrite the following text in a clear, balanced, and professional tone while maintaining the original meaning:",
            'suspenseful': "Rewrite the following text to create suspense and drama, making it more engaging and thrilling while preserving the core message:",
            'inspiring': "Rewrite the following text in an uplifting, motivational, and inspiring tone that encourages and energizes the reader:",
            'cheerful': "Rewrite the following text in a bright, happy, and energetic tone that conveys joy and positivity:",
            'sad': "Rewrite the following text in a soft, somber, and emotional tone that conveys melancholy and reflection:",
            'angry': "Rewrite the following text with intensity and passion, conveying strong emotions and determination:",
            'playful': "Rewrite the following text in a fun, lively, and whimsical tone that is entertaining and lighthearted:",
            'calm': "Rewrite the following text in a relaxed, soothing, and peaceful tone that promotes tranquility:",
            'confident': "Rewrite the following text in an assured, persuasive, and authoritative tone that conveys certainty and leadership:"
        }

TONE_PROMPTS = get_tone_prompts()

def clean_tone_prefix(text, tone):
    """Remove any tone prefix from the text"""
    if not text:
        return text
    # Remove any [TONE] prefix (case insensitive)
    pattern = re.compile(r'^\s*\[?\s*' + re.escape(tone.upper()) + r'\s*TONE\s*\]?\s*', re.IGNORECASE)
    return pattern.sub('', text).strip()

def call_ai_llm(text, tone):
    """Call AI LLM for tone-adaptive text rewriting (Hugging Face first, then Watson fallback)"""
    try:
        # First try Hugging Face
        logger.info(f"Attempting text rewriting with Hugging Face (tone: {tone})")
        result = hf_service.rewrite_text(text, tone)
        
        # Clean any tone prefix from the result
        if result:
            cleaned_result = clean_tone_prefix(result, tone)
            logger.info("Text rewriting successful with Hugging Face")
            return cleaned_result
        
        logger.info("Hugging Face not available, trying Watson fallback")
        # Fallback to Watson if Hugging Face fails
        return call_watsonx_llm(text, tone)
        
    except Exception as e:
        logger.error(f"Error in AI text rewriting: {e}")
        # Return original text without tone prefix in case of error
        return text

def call_watsonx_llm(text, tone):
    """Call IBM Watsonx LLM for tone-adaptive text rewriting (fallback)"""
    try:
        # Check if we have valid credentials
        if WATSONX_API_KEY == 'YOUR_WATSONX_API_KEY' or not WATSONX_API_KEY:
            logger.info("Using mock rewriting (no valid Watson credentials)")
            return text  # Return text without tone prefix
        
        # Get access token
        access_token = get_access_token()
        if not access_token:
            logger.warning("Failed to get access token, using fallback")
            return f"[{tone.upper()} TONE] {text}"
        
        # Prepare the prompt
        prompt = f"{TONE_PROMPTS.get(tone, TONE_PROMPTS['neutral'])}\n\nOriginal text: {text}\n\nRewritten text:"
        
        # Prepare headers and payload for Watsonx API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        payload = {
            'input': prompt,
            'parameters': {
                'decoding_method': 'greedy',
                'max_new_tokens': 500,
                'temperature': 0.7,
                'repetition_penalty': 1.1
            },
            'model_id': 'ibm/granite-13b-chat-v2',
            'project_id': WATSONX_PROJECT_ID
        }
        
        # Make API call to Watsonx
        response = requests.post(
            f"{WATSONX_URL}/ml/v1/text/generation",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['results'][0]['generated_text'].strip()
            return generated_text
        else:
            logger.error(f"Watsonx API error: {response.status_code} - {response.text}")
            return text  # Return original text without tone prefix
            
    except Exception as e:
        logger.error(f"Error calling Watsonx LLM: {e}")
        return text  # Return original text without tone prefix

def get_access_token():
    """Get IBM Cloud access token"""
    try:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
            'apikey': WATSONX_API_KEY
        }
        
        response = requests.post(
            'https://iam.cloud.ibm.com/identity/token',
            headers=headers,
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            logger.error(f"Failed to get access token: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None

# --- Authentication Endpoints ---
@app.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Additional optional fields
        optional_fields = ['phone', 'location', 'date_of_birth', 'university', 'course', 'year', 'roll_number', 'gpa', 'bio']
        additional_data = {k: v for k, v in data.items() if k in optional_fields and v}
        
        # Register user
        user, message = db_manager.register_user(
            name=data['name'],
            email=data['email'],
            password=data['password'],
            **additional_data
        )
        
        if user:
            return jsonify({
                'message': message,
                'user': user
            }), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user login"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Authenticate user
        user, message = db_manager.authenticate_user(
            email=data['email'],
            password=data['password']
        )
        
        if user:
            return jsonify({
                'message': message,
                'user': user
            }), 200
        else:
            return jsonify({'error': message}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/auth/me', methods=['GET'])
def get_current_user():
    """Get current user profile (requires user_id in query params for now)"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user = db_manager.get_user(user_id)
        if user:
            # Remove password hash from response
            user_data = dict(user)
            if 'password_hash' in user_data:
                del user_data['password_hash']
            return jsonify({'user': user_data}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({'error': 'Failed to get user'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'tts': tts is not None,
            'watsonx': WATSONX_API_KEY != 'YOUR_WATSONX_API_KEY'
        }
    })

@app.route('/rewrite', methods=['POST'])
def rewrite():
    """Endpoint for tone-adaptive text rewriting"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        tone = data.get('tone', 'neutral').lower()
        user_email = data.get('user_email', 'default@echoverse.com')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if tone not in TONE_PROMPTS:
            return jsonify({'error': f'Invalid tone. Available tones: {list(TONE_PROMPTS.keys())}'}), 400
        
        logger.info(f"Rewriting text with tone: {tone}")
        
        # Call AI LLM for rewriting (Hugging Face first, Watson fallback)
        rewritten_text = call_ai_llm(text, tone)
        
        # Get or create user
        user = db_manager.get_user_by_email(user_email)
        if not user:
            # Create default user with correct parameters
            user_id = db_manager.create_user(
                name='Default User',
                email=user_email,
                phone='',
                location='',
                university='',
                course='',
                year='',
                roll_number='',
                gpa=0.0,
                bio=''
            )
        else:
            user_id = user['id']
        
        # Save to database
        history_id = db_manager.save_audio_history(
            user_id=user_id,
            original_text=text,
            rewritten_text=rewritten_text,
            tone=tone,
            voice=data.get('voice', 'allison')
        )
        
        return jsonify({
            'success': True,
            'original_text': text,
            'rewritten_text': rewritten_text,
            'tone': tone,
            'history_id': history_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in rewrite endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/synthesize', methods=['POST'])
def synthesize():
    """Endpoint for text-to-speech conversion"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        voice = data.get('voice', 'david').lower()
        tone = data.get('tone', 'neutral').lower()
        history_id = data.get('history_id')
        user_id = data.get('user_id')  # Add user_id to track ownership
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if voice not in VOICE_MAPPING:
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICE_MAPPING.keys())}'}), 400
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        logger.info(f"Synthesizing text for user {user_id} with voice: {voice}, tone: {tone}")
        
        # If no history_id provided, create a new history record
        if not history_id:
            history_id = db_manager.save_audio_history(
                user_id=user_id,
                original_text=text,
                rewritten_text=text,  # If not rewritten, original text is the same
                tone=tone,
                voice=voice
            )
            logger.info(f"Created new history record with ID: {history_id}")
        
        # Try Hugging Face TTS first
        try:
            audio_data = hf_service.synthesize_speech(text, voice, tone)
            
            if audio_data:
                logger.info("TTS successful with Hugging Face")
                
                # Create permanent file for audio storage
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'echoverse_{user_id}_{voice}_{timestamp}.wav'
                audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                file_path = os.path.join(audio_dir, filename)
                
                # Save audio file
                with open(file_path, 'wb') as f:
                    f.write(audio_data)
                
                file_size = len(audio_data)
                
                # Update database with audio file info
                if history_id:
                    try:
                        db_manager.update_audio_history_status(history_id, 'completed', file_path)
                        
                        # Save download record
                        download_id = db_manager.save_download(
                            user_id=user_id,
                            history_id=history_id,
                            original_filename=f'audiobook_{timestamp}.wav',
                            stored_filename=filename,
                            file_path=file_path,
                            file_size=file_size,
                            mime_type='audio/wav'
                        )
                        logger.info(f"Saved download record with ID: {download_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to update database: {e}")
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=f'echoverse_{voice}_{timestamp}.wav',
                    mimetype='audio/wav'
                )
            else:
                logger.info("Hugging Face TTS not available, trying Watson fallback")
                
        except Exception as e:
            logger.warning(f"Hugging Face TTS error: {e}, trying Watson fallback")
        
        # Fallback to Watson TTS
        if not tts:
            return jsonify({'error': 'Text-to-Speech service not available'}), 503
        
        # Convert voice name to Watson voice ID
        watson_voice = VOICE_MAPPING[voice]
        
        # Generate audio using Watson TTS with highest quality settings
        try:
            # Use WAV format with high sampling rate for best quality
            response = tts.synthesize(
                text=text,
                voice=watson_voice,
                accept='audio/wav;rate=22050',  # High-quality WAV at 22050 Hz
                rate_percentage=0,             # Normal speech rate
                pitch_percentage=0,            # Normal pitch
                volume_percentage=0            # Normal volume
            ).get_result()
            
            # Create permanent file for audio storage with high quality
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'echoverse_{user_id}_{voice}_{timestamp}_hq.wav'
            audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
            os.makedirs(audio_dir, exist_ok=True)
            file_path = os.path.join(audio_dir, filename)
            
            # Save high-quality audio file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            
            # Update database with audio file info
            if history_id:
                try:
                    db_manager.update_audio_history_status(history_id, 'completed', file_path)
                    
                    # Save download record
                    download_id = db_manager.save_download(
                        user_id=user_id,
                        history_id=history_id,
                        original_filename=f'audiobook_hq_{timestamp}.wav',
                        stored_filename=filename,
                        file_path=file_path,
                        file_size=file_size,
                        mime_type='audio/wav'
                    )
                    logger.info(f"Saved high-quality download record with ID: {download_id}")
                    
                except Exception as e:
                    logger.warning(f"Failed to update database: {e}")
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f'echoverse_hq_{voice}_{timestamp}.wav',
                mimetype='audio/wav'
            )
                
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return jsonify({'error': 'Failed to synthesize audio'}), 500
            
    except Exception as e:
        logger.error(f"Error in synthesize endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/audio/<int:history_id>', methods=['GET'])
def get_audio_file(history_id):
    """Serve audio file by history ID"""
    try:
        # Get the current user from the token if needed
        # For now, we'll allow access without authentication for demo purposes
        
        # Get audio file path from database
        history_item = db_manager.get_audio_history_by_id(history_id)
        
        if not history_item:
            return jsonify({'error': 'Audio file not found'}), 404
        
        audio_file_path = history_item.get('audio_file_path')
        if not audio_file_path or not os.path.exists(audio_file_path):
            return jsonify({'error': 'Audio file not found on disk'}), 404
        
        # Serve the audio file
        return send_file(
            audio_file_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name=f'echoverse_audio_{history_id}.mp3'
        )
        
    except Exception as e:
        logger.error(f"Error serving audio file: {e}")
        return jsonify({'error': 'Failed to serve audio file'}), 500

@app.route('/downloads', methods=['GET'])
def get_downloads():
    """Get user's generated audio files (downloads)"""
    try:
        # For demo purposes, we'll return mock data that matches localStorage structure
        # In a real app, this would get data from the database for the authenticated user
        
        mock_downloads = [
            {
                'id': 1,
                'originalText': 'This is a sample text that was converted to audio.',
                'rewrittenText': 'Here is sample content that was transformed into speech audio.',
                'tone': 'cheerful',
                'voice': 'lisa',
                'timestamp': '2024-01-15T10:30:00.000Z',
                'audioGenerated': True
            },
            {
                'id': 2,
                'originalText': 'Another example of text to speech conversion.',
                'rewrittenText': 'Another demonstration of text-to-speech technology.',
                'tone': 'inspiring',
                'voice': 'michael',
                'timestamp': '2024-01-14T15:45:00.000Z',
                'audioGenerated': True
            }
        ]
        
        return jsonify({'downloads': mock_downloads})
        
    except Exception as e:
        logger.error(f"Error getting downloads: {e}")
        return jsonify({'error': 'Failed to get downloads'}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    """Get available voices based on system capabilities"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        available_voices = []
        voice_mapping = {
            'david': {'name': 'David', 'description': 'Confident and clear male voice', 'gender': 'male'},
            'zira': {'name': 'Zira', 'description': 'Professional and warm female voice', 'gender': 'female'},
            'heera': {'name': 'Heera', 'description': 'Expressive and engaging female voice', 'gender': 'female'},
            'mark': {'name': 'Mark', 'description': 'Strong and authoritative male voice', 'gender': 'male'},
            'ravi': {'name': 'Ravi', 'description': 'Smooth and articulate male voice', 'gender': 'male'}
        }
        
        if voices:
            # Try to detect all available voices
            detected_voices = set()
            for i, voice in enumerate(voices):
                voice_name_lower = voice.name.lower()
                
                # Check for each possible voice
                for voice_id, voice_info in voice_mapping.items():
                    if voice_id in voice_name_lower or voice_info['name'].lower() in voice_name_lower:
                        if voice_id not in detected_voices:
                            available_voices.append({
                                'id': voice_id,
                                'name': voice_info['name'],
                                'description': voice_info['description'],
                                'gender': voice_info['gender']
                            })
                            detected_voices.add(voice_id)
        
        # If we didn't detect all voices from the system, add the ones we know should be available
        # based on Windows Speech settings
        if len(available_voices) < 5:
            for voice_id, voice_info in voice_mapping.items():
                if not any(v['id'] == voice_id for v in available_voices):
                    available_voices.append({
                        'id': voice_id,
                        'name': voice_info['name'],
                        'description': voice_info['description'] + ' (May need to be enabled in Windows Settings)',
                        'gender': voice_info['gender']
                    })
        
        return jsonify({
            'voices': available_voices,
            'message': f'Found {len(available_voices)} voice(s). Some voices may need to be enabled in Windows Speech settings.',
            'note': 'If voices are not working, please check Settings > Time & Language > Speech to ensure all voices are properly installed.'
        })
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        # Fallback to all 5 voices
        return jsonify({
            'voices': [
                {'id': 'david', 'name': 'David', 'description': 'Confident and clear male voice', 'gender': 'male'},
                {'id': 'zira', 'name': 'Zira', 'description': 'Professional and warm female voice', 'gender': 'female'},
                {'id': 'heera', 'name': 'Heera', 'description': 'Expressive and engaging female voice', 'gender': 'female'},
                {'id': 'mark', 'name': 'Mark', 'description': 'Strong and authoritative male voice', 'gender': 'male'},
                {'id': 'ravi', 'name': 'Ravi', 'description': 'Smooth and articulate male voice', 'gender': 'male'}
            ],
            'error': 'Using fallback voices due to system error'
        })

@app.route('/debug/system-voices', methods=['GET'])
def get_system_voices():
    """Get available system voices for debugging"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        system_voices = []
        if voices:
            for i, voice in enumerate(voices):
                system_voices.append({
                    'index': i,
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', []),
                    'gender': getattr(voice, 'gender', 'unknown'),
                    'age': getattr(voice, 'age', 'unknown')
                })
        
        return jsonify({
            'system_voices': system_voices,
            'total_count': len(system_voices)
        })
    except Exception as e:
        logger.error(f"Error getting system voices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug/voice-installation-info', methods=['GET'])
def get_voice_installation_info():
    """Provide information about installing additional voices"""
    return jsonify({
        'message': 'To ensure all 5 voices work properly on Windows:',
        'steps': [
            '1. Go to Settings > Time & Language > Speech',
            '2. Under "Voices" section, make sure all 5 voices are visible: David, Zira, Heera, Mark, Ravi',
            '3. If voices are missing, click "Add voices" to download them',
            '4. Select each voice and test it in Windows settings',
            '5. Restart the EchoVerse application after making changes'
        ],
        'available_voices': [
            'Microsoft David - Male voice',
            'Microsoft Zira - Female voice', 
            'Microsoft Heera - Female voice',
            'Microsoft Mark - Male voice',
            'Microsoft Ravi - Male voice'
        ],
        'current_status': 'System should have all 5 voices available',
        'troubleshooting': [
            'If a voice produces no audio, it may need to be re-downloaded',
            'Some voices may require additional language packs',
            'Check Windows Speech settings to ensure voices are properly installed'
        ]
    })

@app.route('/debug/test-all-voices', methods=['GET'])
def test_all_voices():
    """Test all available voices"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        test_results = []
        test_text = "Hello, this is a voice test."
        
        for i, voice in enumerate(voices):
            try:
                engine.setProperty('voice', voice.id)
                # Test if voice can be set successfully
                current_voice = engine.getProperty('voice')
                test_results.append({
                    'index': i,
                    'name': voice.name,
                    'id': voice.id,
                    'gender': getattr(voice, 'gender', 'Unknown'),
                    'status': 'Available' if current_voice == voice.id else 'May have issues'
                })
            except Exception as e:
                test_results.append({
                    'index': i,
                    'name': voice.name,
                    'id': voice.id,
                    'status': f'Error: {str(e)}'
                })
        
        return jsonify({
            'test_results': test_results,
            'total_voices': len(test_results),
            'message': 'Voice availability test completed'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/voices/available', methods=['GET'])
def get_available_voices():
    """Get voices that are actually available on the system"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        available_voices = []
        if voices:
            for i, voice in enumerate(voices):
                # Create user-friendly voice options based on actual system voices
                if 'david' in voice.name.lower() or 'male' in str(getattr(voice, 'gender', '')).lower():
                    available_voices.append({
                        'id': 'david',
                        'name': 'David',
                        'description': 'Confident male voice',
                        'gender': 'male',
                        'system_voice': voice.name,
                        'system_index': i
                    })
                elif 'zira' in voice.name.lower() or 'female' in str(getattr(voice, 'gender', '')).lower():
                    available_voices.append({
                        'id': 'zira',
                        'name': 'Zira', 
                        'description': 'Professional female voice',
                        'gender': 'female',
                        'system_voice': voice.name,
                        'system_index': i
                    })
        
        return jsonify({
            'voices': available_voices,
            'total_count': len(available_voices),
            'note': 'These are the actual voices available on your system'
        })
    except Exception as e:
        logger.error(f"Error getting available voices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/tones', methods=['GET'])
def get_tones():
    """Get available tones"""
    try:
        tones = db_manager.get_tones()
        return jsonify({
            'tones': [
                {
                    'id': tone['tone_id'],
                    'name': tone['tone_name'],
                    'description': tone['description']
                } for tone in tones
            ]
        })
    except Exception as e:
        logger.error(f"Error getting tones: {e}")
        # Fallback to hardcoded tones
        return jsonify({
            'tones': [
                {'id': 'neutral', 'name': 'Neutral', 'description': 'Clear and balanced narration'},
                {'id': 'cheerful', 'name': 'Cheerful', 'description': 'Bright, happy, and energetic'},
                {'id': 'suspenseful', 'name': 'Suspenseful', 'description': 'Dramatic and engaging delivery'},
                {'id': 'inspiring', 'name': 'Inspiring', 'description': 'Uplifting and motivational tone'},
                {'id': 'sad', 'name': 'Sad', 'description': 'Soft, somber, and emotional'},
                {'id': 'angry', 'name': 'Angry', 'description': 'Intense and passionate delivery'},
                {'id': 'playful', 'name': 'Playful', 'description': 'Fun, lively, and whimsical'},
                {'id': 'calm', 'name': 'Calm', 'description': 'Relaxed and soothing narration'},
                {'id': 'confident', 'name': 'Confident', 'description': 'Assured and persuasive'}
            ]
        })

# Test endpoint
@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({'status': 'Backend is working!', 'message': 'CORS should be configured properly'})

# User Profile Endpoints
@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if user already exists
        existing_user = db_manager.get_user_by_email(data['email'])
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        user_id = db_manager.create_user(data)
        user = db_manager.get_user_by_email(data['email'])
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user': user
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<email>', methods=['GET'])
def get_user(email):
    """Get user by email"""
    try:
        user = db_manager.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': user
        })
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<email>', methods=['PUT'])
def update_user(email):
    """Update user information"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user = db_manager.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db_manager.update_user(user['id'], data)
        updated_user = db_manager.get_user_by_email(email)
        
        return jsonify({
            'success': True,
            'user': updated_user
        })
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# History Endpoints
@app.route('/history', methods=['POST'])
def save_history():
    """Save a new history entry"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        user_id = data.get('user_id')
        original_text = data.get('original_text', '')
        rewritten_text = data.get('rewritten_text', '')
        tone = data.get('tone', 'neutral')
        voice = data.get('voice', 'david')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        if not original_text:
            return jsonify({'error': 'Original text is required'}), 400
        
        # Save to database
        history_id = db_manager.save_audio_history(
            user_id=user_id,
            original_text=original_text,
            rewritten_text=rewritten_text,
            tone=tone,
            voice=voice
        )
        
        if history_id:
            return jsonify({
                'success': True,
                'history_id': history_id,
                'message': 'History saved successfully'
            })
        else:
            return jsonify({'error': 'Failed to save history'}), 500
        
    except Exception as e:
        logger.error(f"Error saving history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/users/<email>/history', methods=['GET'])
def get_user_history(email):
    """Get user's audio history"""
    try:
        user = db_manager.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        limit = request.args.get('limit', 50, type=int)
        history = db_manager.get_user_audio_history(user['id'], limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/history/<int:history_id>', methods=['DELETE'])
def delete_history_item(history_id):
    """Delete a history item"""
    try:
        data = request.get_json()
        user_email = data.get('user_email') if data else None
        
        if not user_email:
            return jsonify({'error': 'User email is required'}), 400
        
        user = db_manager.get_user_by_email(user_email)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db_manager.delete_audio_history(history_id, user['id'])
        
        return jsonify({
            'success': True,
            'message': 'History item deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting history item: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# --- Download Management Endpoints ---
@app.route('/downloads/<int:user_id>', methods=['GET'])
def get_user_downloads(user_id):
    """Get all downloads for a user"""
    try:
        limit = request.args.get('limit', 50, type=int)
        downloads = db_manager.get_user_downloads(user_id, limit)
        
        # Format the downloads data
        formatted_downloads = []
        for download in downloads:
            formatted_downloads.append({
                'id': download['id'],
                'history_id': download['history_id'],
                'original_filename': download['original_filename'],
                'stored_filename': download['stored_filename'],
                'file_size': download['file_size'],
                'mime_type': download['mime_type'],
                'download_count': download['download_count'],
                'created_at': download['created_at'].isoformat() if download['created_at'] else None,
                'last_downloaded_at': download['last_downloaded_at'].isoformat() if download['last_downloaded_at'] else None,
                'original_text': download['original_text'][:100] + '...' if len(download['original_text']) > 100 else download['original_text'],
                'tone': download['tone'],
                'voice': download['voice']
            })
        
        return jsonify({
            'success': True,
            'downloads': formatted_downloads,
            'total': len(formatted_downloads)
        })
        
    except Exception as e:
        logger.error(f"Error getting user downloads: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/downloads/file/<int:download_id>', methods=['GET'])
def download_audio_file(download_id):
    """Download audio file by download ID"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        download = db_manager.get_download_by_id(download_id, user_id)
        if not download:
            return jsonify({'error': 'Download not found'}), 404
        
        # Check if file exists
        if not os.path.exists(download['file_path']):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Update download statistics
        db_manager.update_download_stats(download_id)
        
        return send_file(
            download['file_path'],
            as_attachment=True,
            download_name=download['original_filename'],
            mimetype=download['mime_type']
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/downloads/<int:download_id>', methods=['DELETE'])
def delete_download(download_id):
    """Delete a download record and its file"""
    try:
        data = request.get_json()
        user_id = data.get('user_id') if data else None
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        success = db_manager.delete_download(download_id, user_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Download deleted successfully'
            })
        else:
            return jsonify({'error': 'Download not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting download: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/download-audio/<filename>', methods=['GET'])
def serve_audio_file(filename):
    """Serve audio files for story narration"""
    try:
        audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
        file_path = os.path.join(audio_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=False,
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        logger.error(f"Error serving audio file: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# --- Enhanced History Endpoints ---
@app.route('/history/<int:user_id>', methods=['GET'])
def get_user_history_by_id(user_id):
    """Get audio generation history for a user by ID"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = db_manager.get_user_audio_history(user_id, limit)
        
        # Format the history data
        formatted_history = []
        for item in history:
            formatted_history.append({
                'id': item['id'],
                'original_text': item['original_text'],
                'rewritten_text': item['rewritten_text'],
                'tone': item['tone'],
                'voice': item['voice'],
                'audio_generated': item['audio_generated'],
                'processing_status': item['processing_status'],
                'created_at': item['created_at'].isoformat() if item['created_at'] else None,
                'updated_at': item['updated_at'].isoformat() if item['updated_at'] else None
            })
        
        return jsonify({
            'success': True,
            'history': formatted_history,
            'total': len(formatted_history)
        })
        
    except Exception as e:
        logger.error(f"Error getting user history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/story-narration', methods=['POST'])
def story_narration():
    """Endpoint for intelligent story narration with multiple voices and tones"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        user_id = data.get('user_id')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        logger.info(f"Processing story narration for user {user_id}")
        
        # Analyze the story and create segments
        segments = analyze_story_content(text)
        
        return jsonify({
            'success': True,
            'segments': segments,
            'total_segments': len(segments),
            'voices_used': list(set([seg['voice'] for seg in segments])),
            'tones_used': list(set([seg['tone'] for seg in segments]))
        })
        
    except Exception as e:
        logger.error(f"Error in story narration endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/story-narration-audio', methods=['POST'])
def story_narration_audio():
    """Generate audio for story segments and return URLs"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        voice = data.get('voice', 'david').lower()
        tone = data.get('tone', 'neutral').lower()
        user_id = data.get('user_id')
        segment_id = data.get('segment_id', 0)
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if voice not in VOICE_MAPPING:
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICE_MAPPING.keys())}'}), 400
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        logger.info(f"Generating story segment audio for user {user_id} with voice: {voice}, tone: {tone}")
        
        # Create a history record for this segment
        history_id = db_manager.save_audio_history(
            user_id=user_id,
            original_text=text,
            rewritten_text=text,
            tone=tone,
            voice=voice
        )
        
        # Try Hugging Face TTS first
        audio_data = None
        file_path = None
        
        try:
            audio_data = hf_service.synthesize_speech(text, voice, tone)
            
            if audio_data:
                logger.info("TTS successful with Hugging Face")
                
                # Create permanent file for audio storage
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'story_segment_{user_id}_{voice}_{segment_id}_{timestamp}.wav'
                audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                file_path = os.path.join(audio_dir, filename)
                
                # Save audio file
                with open(file_path, 'wb') as f:
                    f.write(audio_data)
                
                file_size = len(audio_data)
                
        except Exception as e:
            logger.warning(f"Hugging Face TTS error: {e}, trying Watson fallback")
        
        # Fallback to Watson TTS if Hugging Face failed
        if not audio_data and tts:
            try:
                watson_voice = VOICE_MAPPING[voice]
                
                response = tts.synthesize(
                    text=text,
                    voice=watson_voice,
                    accept='audio/wav;rate=22050',
                    rate_percentage=0,
                    pitch_percentage=0,
                    volume_percentage=0
                ).get_result()
                
                # Create permanent file for audio storage
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'story_segment_{user_id}_{voice}_{segment_id}_{timestamp}_watson.wav'
                audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                file_path = os.path.join(audio_dir, filename)
                
                # Save audio file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                audio_data = response.content
                
            except Exception as e:
                logger.error(f"Watson TTS error: {e}")
                return jsonify({'error': 'Failed to generate audio'}), 500
        
        if not audio_data:
            return jsonify({'error': 'TTS service not available'}), 503
        
        # Update database with audio file info
        try:
            db_manager.update_audio_history_status(history_id, 'completed', file_path)
            
            # Save download record
            download_id = db_manager.save_download(
                user_id=user_id,
                history_id=history_id,
                original_filename=f'story_segment_{segment_id}.wav',
                stored_filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type='audio/wav'
            )
            
        except Exception as e:
            logger.warning(f"Failed to update database: {e}")
        
        # Return JSON with audio URL
        audio_url = f'/download-audio/{filename}'
        
        return jsonify({
            'success': True,
            'audio_url': audio_url,
            'filename': filename,
            'file_size': file_size,
            'voice': voice,
            'tone': tone,
            'segment_id': segment_id
        })
        
    except Exception as e:
        logger.error(f"Error in story narration audio endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/story-narration-merged', methods=['POST'])
def story_narration_merged():
    """Generate merged audio for all story segments"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        user_id = data.get('user_id')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        logger.info(f"Generating merged story audio for user {user_id}")
        
        # Analyze the story and create segments
        segments = analyze_story_content(text)
        
        if not segments:
            return jsonify({'error': 'No story segments found'}), 400
        
        # Generate audio for each segment
        audio_files = []
        temp_files = []
        
        for i, segment in enumerate(segments):
            segment_text = segment['text']
            voice = segment['voice']
            tone = segment['tone']
            
            logger.info(f"Generating audio for segment {i+1}: {voice} ({tone})")
            
            # Try Hugging Face TTS first
            audio_data = None
            
            try:
                audio_data = hf_service.synthesize_speech(segment_text, voice, tone)
                if audio_data:
                    logger.info(f"TTS successful with Hugging Face for segment {i+1}")
            except Exception as e:
                logger.warning(f"Hugging Face TTS error for segment {i+1}: {e}")
            
            # Fallback to Watson TTS if Hugging Face failed
            if not audio_data and tts:
                try:
                    watson_voice = VOICE_MAPPING[voice]
                    response = tts.synthesize(
                        text=segment_text,
                        voice=watson_voice,
                        accept='audio/wav;rate=22050',
                        rate_percentage=0,
                        pitch_percentage=0,
                        volume_percentage=0
                    ).get_result()
                    
                    audio_data = response.content
                    logger.info(f"TTS successful with Watson for segment {i+1}")
                    
                except Exception as e:
                    logger.error(f"Watson TTS error for segment {i+1}: {e}")
                    continue
            
            if audio_data:
                # Save temporary file
                temp_filename = f'temp_segment_{user_id}_{i}.wav'
                temp_path = os.path.join(os.path.dirname(__file__), 'temp', temp_filename)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                with open(temp_path, 'wb') as f:
                    f.write(audio_data)
                
                audio_files.append(temp_path)
                temp_files.append(temp_path)
        
        if not audio_files:
            return jsonify({'error': 'Failed to generate any audio segments'}), 500
        
        # Merge all audio files
        try:
            from pydub import AudioSegment
            
            # Load first audio file
            merged_audio = AudioSegment.from_wav(audio_files[0])
            
            # Add subsequent files with small pauses
            for audio_file in audio_files[1:]:
                # Add a small pause between segments (0.5 seconds)
                pause = AudioSegment.silent(duration=500)
                segment_audio = AudioSegment.from_wav(audio_file)
                merged_audio = merged_audio + pause + segment_audio
            
            # Save merged audio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            merged_filename = f'story_merged_{user_id}_{timestamp}.wav'
            audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
            os.makedirs(audio_dir, exist_ok=True)
            merged_path = os.path.join(audio_dir, merged_filename)
            
            merged_audio.export(merged_path, format="wav")
            
            # Get file size
            file_size = os.path.getsize(merged_path)
            
            # Create history record for merged audio
            history_id = db_manager.save_audio_history(
                user_id=user_id,
                original_text=text,
                rewritten_text="Story Narration (Merged)",
                tone="multiple",
                voice="multiple"
            )
            
            # Update database with audio file info
            try:
                db_manager.update_audio_history_status(history_id, 'completed', merged_path)
                
                # Save download record
                download_id = db_manager.save_download(
                    user_id=user_id,
                    history_id=history_id,
                    original_filename='story_merged.wav',
                    stored_filename=merged_filename,
                    file_path=merged_path,
                    file_size=file_size,
                    mime_type='audio/wav'
                )
                
            except Exception as e:
                logger.warning(f"Failed to update database: {e}")
            
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            # Return merged audio URL
            audio_url = f'/download-audio/{merged_filename}'
            
            return jsonify({
                'success': True,
                'audio_url': audio_url,
                'filename': merged_filename,
                'file_size': file_size,
                'segments_count': len(segments),
                'duration_estimate': len(merged_audio) / 1000  # in seconds
            })
            
        except ImportError:
            return jsonify({'error': 'Audio merging not available. Install pydub: pip install pydub'}), 500
        except Exception as e:
            logger.error(f"Error merging audio files: {e}")
            
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return jsonify({'error': 'Failed to merge audio files'}), 500
        
    except Exception as e:
        logger.error(f"Error in story narration merged endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def analyze_story_content(text):
    """Analyze story content and assign voices and tones"""
    import re
    
    # Available voices for different characters
    voices = ['david', 'zira', 'heera', 'mark', 'ravi']
    
    # Emotion to tone mapping
    emotion_mapping = {
        'cheerful': 'cheerful',
        'happy': 'cheerful',
        'excited': 'cheerful',
        'playful': 'cheerful',
        'joy': 'cheerful',
        'laugh': 'cheerful',
        'smile': 'cheerful',
        'sad': 'sad',
        'cry': 'sad',
        'weep': 'sad',
        'sorrow': 'sad',
        'tear': 'sad',
        'angry': 'angry',
        'mad': 'angry',
        'furious': 'angry',
        'rage': 'angry',
        'shout': 'angry',
        'calm': 'calm',
        'peaceful': 'calm',
        'quiet': 'calm',
        'whisper': 'calm',
        'serene': 'calm',
        'nervous': 'suspenseful',
        'scared': 'suspenseful',
        'afraid': 'suspenseful',
        'worry': 'suspenseful',
        'anxious': 'suspenseful',
        'suspenseful': 'suspenseful',
        'confident': 'confident',
        'proud': 'confident',
        'strong': 'confident',
        'brave': 'confident',
        'bold': 'confident',
        'inspiring': 'confident'
    }
    
    # Split text into lines first to detect character dialogue format
    lines = text.split('\n')
    segments = []
    character_voices = {}  # Track voices assigned to characters
    narrator_voice = voices[0]  # Default narrator voice
    current_voice_index = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        voice = narrator_voice
        tone = 'neutral'
        character = 'Narrator'
        is_dialogue = False
        
        # Check for character dialogue format: "CharacterName (emotion): dialogue"
        character_match = re.match(r'(\w+)\s*\(([^)]+)\):\s*["\']?([^"\']*)["\']?', line)
        if character_match:
            character_name = character_match.group(1).title()
            emotion_hint = character_match.group(2).lower().strip()
            dialogue_text = character_match.group(3).strip()
            
            # Assign voice to character
            if character_name not in character_voices:
                character_voices[character_name] = voices[current_voice_index % len(voices)]
                current_voice_index += 1
            
            voice = character_voices[character_name]
            character = character_name
            is_dialogue = True
            
            # Map emotion hint to tone
            tone = emotion_mapping.get(emotion_hint, 'neutral')
            
            # Use the dialogue text as the main text
            text_to_speak = dialogue_text
        else:
            # Check for regular dialogue with quotes
            dialogue_match = re.search(r'"([^"]*)"', line)
            if dialogue_match:
                is_dialogue = True
                # Extract speaker if mentioned
                speaker_match = re.search(r'(\w+)\s+said|said\s+(\w+)|(\w+)\s+asked|asked\s+(\w+)|(\w+)\s+replied|replied\s+(\w+)', line.lower())
                
                if speaker_match:
                    speaker = next(filter(None, speaker_match.groups())).title()
                    if speaker not in character_voices:
                        character_voices[speaker] = voices[current_voice_index % len(voices)]
                        current_voice_index += 1
                    voice = character_voices[speaker]
                    character = speaker
                else:
                    # Generic character if no speaker identified
                    character_num = len([c for c in character_voices.keys() if c.startswith('Character')]) + 1
                    character = f"Character {character_num}"
                    if character not in character_voices:
                        character_voices[character] = voices[current_voice_index % len(voices)]
                        current_voice_index += 1
                    voice = character_voices[character]
            
            text_to_speak = line
        
        # Detect emotion in text if not already set
        if tone == 'neutral':
            text_lower = text_to_speak.lower()
            for emotion, mapped_tone in emotion_mapping.items():
                if emotion in text_lower:
                    tone = mapped_tone
                    break
        
        # Detect action/emotional indicators
        if tone == 'neutral':
            if any(word in text_to_speak.lower() for word in ['!', 'exclaimed', 'shouted', 'yelled']):
                tone = 'angry'
            elif any(word in text_to_speak.lower() for word in ['whispered', 'murmured', 'softly']):
                tone = 'calm'
            elif any(word in text_to_speak.lower() for word in ['wondered', 'mysterious', 'strange']):
                tone = 'suspenseful'
        
        # Clean up the text
        if not text_to_speak.endswith(('.', '!', '?')):
            text_to_speak += '.'
        
        segments.append({
            'text': text_to_speak,
            'voice': voice,
            'tone': tone,
            'character': character,
            'emotion': tone if tone != 'neutral' else None,
            'is_dialogue': is_dialogue
        })
    
    return segments

# --- Admin Routes ---
import jwt
from functools import wraps

# JWT secret key - in production, use environment variable
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_admin = payload.get('admin')
            if not current_admin:
                return jsonify({'error': 'Invalid token'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        admin = db_manager.authenticate_admin(email, password)
        if not admin:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate JWT token
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            'admin': {
                'id': admin['id'],
                'email': admin['email'],
                'name': admin['name'],
                'role': admin['role']
            },
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'admin': admin
        })
        
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/metrics', methods=['GET'])
@admin_required
def get_admin_metrics():
    """Get admin dashboard metrics"""
    try:
        metrics = db_manager.get_admin_metrics()
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting admin metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/recent-users', methods=['GET'])
@admin_required
def get_recent_users():
    """Get recent users for admin dashboard"""
    try:
        users = db_manager.get_recent_users(limit=20)
        formatted_users = []
        
        for user in users:
            formatted_users.append({
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'status': user['status'],
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            })
        
        return jsonify({'users': formatted_users})
        
    except Exception as e:
        logger.error(f"Error getting recent users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/system-health', methods=['GET'])
@admin_required
def get_system_health():
    """Get system health metrics"""
    try:
        health = db_manager.get_system_health()
        return jsonify(health)
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/flagged', methods=['GET'])
@admin_required
def get_flagged_content():
    """Get flagged content for admin review"""
    try:
        # Mock data for now - implement actual flagging system later
        return jsonify({'items': []})
        
    except Exception as e:
        logger.error(f"Error getting flagged content: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/actions/suspend-user', methods=['POST'])
@admin_required
def suspend_user():
    """Suspend a user account"""
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Implement user suspension logic here
        # For now, just return success
        return jsonify({'success': True, 'message': 'User suspended'})
        
    except Exception as e:
        logger.error(f"Error suspending user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/actions/add-moderator', methods=['POST'])
@admin_required
def add_moderator():
    """Add a new moderator"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        # Implement moderator addition logic here
        # For now, just return success
        return jsonify({'success': True, 'message': 'Moderator added'})
        
    except Exception as e:
        logger.error(f"Error adding moderator: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/actions/announce', methods=['POST'])
@admin_required
def send_announcement():
    """Send announcement to users"""
    try:
        data = request.json
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Implement announcement logic here
        # For now, just return success
        return jsonify({'success': True, 'message': 'Announcement sent'})
        
    except Exception as e:
        logger.error(f"Error sending announcement: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# --- Student Materials Processing Endpoints ---

@app.route('/process-study-material', methods=['POST'])
def process_study_material():
    """Process uploaded study material (PDF, Word, Text) and extract chapters/topics"""
    try:
        logger.info("Processing study material upload request")
        
        if 'file' not in request.files:
            logger.error("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id')
        
        logger.info(f"Received file: {file.filename}, User ID: {user_id}")
        
        if not user_id:
            logger.error("No user ID provided")
            return jsonify({'error': 'User ID is required'}), 400
            
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            logger.error(f"Unsupported file extension: {file_ext}")
            return jsonify({'error': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, filename)
        
        logger.info(f"Saving file to: {file_path}")
        file.save(file_path)
        
        # Check file size after saving
        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        
        try:
            # Extract text based on file type
            logger.info(f"Extracting text from {file_ext} file")
            if filename.lower().endswith('.pdf'):
                logger.info("Processing PDF file")
                text_content = extract_text_from_pdf(file_path)
            elif filename.lower().endswith(('.doc', '.docx')):
                logger.info("Processing Word document")
                text_content = extract_text_from_word(file_path)
            elif filename.lower().endswith('.txt'):
                logger.info("Processing text file")
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            else:
                logger.error(f"Unsupported file type: {filename}")
                return jsonify({'error': 'Unsupported file type'}), 400
            
            logger.info(f"Successfully extracted {len(text_content)} characters")
            
            if not text_content or len(text_content.strip()) < 50:
                logger.error(f"File appears to be empty or too short. Content length: {len(text_content) if text_content else 0}")
                return jsonify({'error': f'File appears to be empty or contains insufficient readable text. Extracted {len(text_content) if text_content else 0} characters. This might be a scanned PDF or image-based document.'}), 400
            
            # Process the content into chapters and topics
            logger.info("Processing content into chapters and topics")
            processed_material = process_study_content(text_content, filename)
            logger.info(f"Successfully processed into {len(processed_material['chapters'])} chapters")
            
            # Save to database (optional)
            try:
                material_id = db_manager.save_study_material(
                    user_id=user_id,
                    title=processed_material['title'],
                    content=text_content,
                    chapters=json.dumps(processed_material['chapters']),
                    file_type=file.content_type
                )
                processed_material['material_id'] = material_id
            except Exception as e:
                logger.warning(f"Failed to save to database: {e}")
            
            # Clean up temporary file
            os.remove(file_path)
            
            return jsonify({
                'success': True,
                'material': processed_material
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e
            
    except Exception as e:
        logger.error(f"Error processing study material: {e}")
        return jsonify({'error': 'Failed to process study material'}), 500

@app.route('/generate-topic-audio', methods=['POST'])
def generate_topic_audio():
    """Generate audio for a specific topic"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        text = data.get('text', '').strip()
        topic_name = data.get('topic_name', 'topic')
        chapter_name = data.get('chapter_name', 'chapter')
        user_id = data.get('user_id')
        voice = data.get('voice', 'david').lower()
        tone = data.get('tone', 'neutral').lower()
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        if voice not in VOICE_MAPPING:
            return jsonify({'error': f'Invalid voice. Available voices: {list(VOICE_MAPPING.keys())}'}), 400
        
        logger.info(f"Generating topic audio for user {user_id}: {topic_name}")
        
        # Create a history record for this topic
        history_id = db_manager.save_audio_history(
            user_id=user_id,
            original_text=f"{chapter_name} - {topic_name}",
            rewritten_text=text,
            tone=tone,
            voice=voice
        )
        
        # Try Hugging Face TTS first
        audio_data = None
        file_path = None
        
        try:
            audio_data = hf_service.synthesize_speech(text, voice, tone)
            
            if audio_data:
                logger.info("TTS successful with Hugging Face")
                
                # Create filename with topic name
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic_name = re.sub(r'[^\w\s-]', '', topic_name).strip()
                safe_topic_name = re.sub(r'[-\s]+', '_', safe_topic_name)
                filename = f'{safe_topic_name}_{timestamp}.mp3'
                
                audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                file_path = os.path.join(audio_dir, filename)
                
                # Save audio file
                with open(file_path, 'wb') as f:
                    f.write(audio_data)
                
                file_size = len(audio_data)
                
        except Exception as e:
            logger.warning(f"Hugging Face TTS error: {e}, trying Watson fallback")
        
        # Fallback to Watson TTS if Hugging Face failed
        if not audio_data and tts:
            try:
                watson_voice = VOICE_MAPPING[voice]
                
                response = tts.synthesize(
                    text=text,
                    voice=watson_voice,
                    accept='audio/wav;rate=22050',
                    rate_percentage=0,
                    pitch_percentage=0,
                    volume_percentage=0
                ).get_result()
                
                # Create filename with topic name
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic_name = re.sub(r'[^\w\s-]', '', topic_name).strip()
                safe_topic_name = re.sub(r'[-\s]+', '_', safe_topic_name)
                filename = f'{safe_topic_name}_{timestamp}_watson.wav'
                
                audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
                os.makedirs(audio_dir, exist_ok=True)
                file_path = os.path.join(audio_dir, filename)
                
                # Save audio file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                audio_data = response.content
                
            except Exception as e:
                logger.error(f"Watson TTS error: {e}")
                return jsonify({'error': 'Failed to generate audio'}), 500
        
        if not audio_data:
            return jsonify({'error': 'TTS service not available'}), 503
        
        # Update database with audio file info
        try:
            db_manager.update_audio_history_status(history_id, 'completed', file_path)
            
            # Save download record
            download_id = db_manager.save_download(
                user_id=user_id,
                history_id=history_id,
                original_filename=f'{safe_topic_name}.mp3',
                stored_filename=filename,
                file_path=file_path,
                file_size=file_size,
                mime_type='audio/mpeg' if filename.endswith('.mp3') else 'audio/wav'
            )
            
        except Exception as e:
            logger.warning(f"Failed to update database: {e}")
        
        # Return JSON with audio URL
        audio_url = f'/download-audio/{filename}'
        
        return jsonify({
            'success': True,
            'audio_url': audio_url,
            'filename': filename,
            'file_size': file_size,
            'topic_name': topic_name,
            'chapter_name': chapter_name
        })
        
    except Exception as e:
        logger.error(f"Error in topic audio generation endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def extract_text_from_pdf(file_path):
    """Extract text from PDF file with enhanced error handling"""
    try:
        text = ""
        logger.info(f"Attempting to extract text from PDF: {file_path}")
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            logger.info(f"PDF has {len(pdf_reader.pages)} pages")
            
            if len(pdf_reader.pages) == 0:
                raise Exception("PDF has no pages")
            
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        logger.info(f"Extracted {len(page_text)} characters from page {i+1}")
                    else:
                        logger.warning(f"No text found on page {i+1}")
                except Exception as page_error:
                    logger.warning(f"Error extracting text from page {i+1}: {page_error}")
                    continue
            
        logger.info(f"Total extracted text length: {len(text)} characters")
        
        # If no text was extracted, it might be a scanned PDF
        if not text.strip():
            logger.warning("No text extracted from PDF - might be a scanned document")
            # Create a fallback message
            text = "This appears to be a scanned PDF document. Text extraction is not available for image-based PDFs. Please try uploading a text-based PDF or convert your document to a Word/text file."
        
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        # Don't raise the error, return a helpful message instead
        return f"Unable to extract text from this PDF file. Error: {str(e)}. Please try uploading a different format (Word or text file)."

def extract_text_from_word(file_path):
    """Extract text from Word document"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from Word document: {e}")
        raise e

def process_study_content(text, filename):
    """Process study content into chapters and topics"""
    try:
        # Clean and prepare text
        text = text.strip()
        
        # Extract title from filename or first line
        title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        if len(text.split('\n')) > 0:
            first_line = text.split('\n')[0].strip()
            if len(first_line) < 100 and any(word in first_line.lower() for word in ['chapter', 'unit', 'lesson', 'part']):
                title = first_line
        
        # Split into chapters
        chapters = []
        
        # Try to detect chapter patterns
        chapter_patterns = [
            r'chapter\s+\d+[:\.]?\s*(.+?)(?=\n|$)',
            r'unit\s+\d+[:\.]?\s*(.+?)(?=\n|$)',
            r'lesson\s+\d+[:\.]?\s*(.+?)(?=\n|$)',
            r'part\s+\d+[:\.]?\s*(.+?)(?=\n|$)',
            r'\d+\.\s*(.+?)(?=\n|$)'
        ]
        
        chapter_splits = []
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if len(matches) >= 2:  # Need at least 2 chapters
                chapter_splits = matches
                break
        
        if chapter_splits:
            # Process detected chapters
            for i, match in enumerate(chapter_splits):
                chapter_title = match.group(1).strip()
                start_pos = match.end()
                end_pos = chapter_splits[i + 1].start() if i + 1 < len(chapter_splits) else len(text)
                chapter_content = text[start_pos:end_pos].strip()
                
                if chapter_content:
                    topics = extract_topics_from_chapter(chapter_content)
                    chapters.append({
                        'title': chapter_title,
                        'summary': generate_chapter_summary(chapter_content),
                        'topics': topics
                    })
        else:
            # No clear chapters found, create one chapter and extract topics
            topics = extract_topics_from_chapter(text)
            chapters.append({
                'title': title,
                'summary': generate_chapter_summary(text),
                'topics': topics
            })
        
        # Calculate word count
        word_count = len(text.split())
        
        return {
            'title': title,
            'chapters': chapters,
            'word_count': word_count,
            'total_topics': sum(len(chapter['topics']) for chapter in chapters)
        }
        
    except Exception as e:
        logger.error(f"Error processing study content: {e}")
        raise e

def extract_topics_from_chapter(chapter_content):
    """Extract topics from chapter content"""
    try:
        topics = []
        
        # Try to detect topic patterns
        topic_patterns = [
            r'(?:^|\n)\s*(\d+\.\d+\.?\s*.+?)(?=\n|$)',  # 1.1, 1.2, etc.
            r'(?:^|\n)\s*([A-Z][^.!?]*[.!?])(?=\s*\n)',  # Sentences that might be headers
            r'(?:^|\n)\s*([A-Z][A-Za-z\s]+)(?=\n\n)',    # Lines followed by double newline
        ]
        
        # Split by paragraphs as fallback
        paragraphs = [p.strip() for p in chapter_content.split('\n\n') if p.strip()]
        
        if len(paragraphs) <= 3:
            # For short content, create one topic
            topics.append({
                'name': 'Main Content',
                'content': chapter_content.strip()
            })
        else:
            # For longer content, try to create meaningful topics
            topic_size = max(2, len(paragraphs) // 5)  # Create 5 topics max
            
            for i in range(0, len(paragraphs), topic_size):
                topic_paragraphs = paragraphs[i:i + topic_size]
                topic_content = '\n\n'.join(topic_paragraphs)
                
                # Generate topic name from first sentence or paragraph
                first_sentence = topic_paragraphs[0].split('.')[0].strip()
                if len(first_sentence) > 60:
                    first_sentence = first_sentence[:60] + "..."
                
                topic_name = f"Topic {len(topics) + 1}: {first_sentence}"
                
                topics.append({
                    'name': topic_name,
                    'content': topic_content
                })
        
        return topics
        
    except Exception as e:
        logger.error(f"Error extracting topics: {e}")
        # Fallback: return the entire content as one topic
        return [{
            'name': 'Main Content',
            'content': chapter_content
        }]

def generate_chapter_summary(content):
    """Generate a brief summary of chapter content"""
    try:
        # Simple summary: first 200 characters
        summary = content.strip()[:200]
        if len(content) > 200:
            summary += "..."
        return summary
    except:
        return "Chapter content available for audio generation."

if __name__ == '__main__':
    logger.info("Starting EchoVerse backend server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
