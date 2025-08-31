"""
Hugging Face API Integration for EchoVerse
Uses IBM Granite models and TTS models via Hugging Face Inference API
"""

import os
import requests
import json
import logging
import tempfile
import base64
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Reload environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """Service for interacting with Hugging Face APIs"""
    
    def __init__(self):
        # Reload environment to ensure latest values
        load_dotenv()
        self.api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        self.text_model = os.getenv('HUGGINGFACE_TEXT_MODEL', 'ibm-granite/granite-3.3-8b-instruct')
        # Use high-quality TTS models
        self.tts_model = os.getenv('HUGGINGFACE_TTS_MODEL', 'microsoft/speecht5_tts')
        # Alternative high-quality models to try
        self.tts_models = [
            'microsoft/speecht5_tts',
            'espnet/kan-bayashi_ljspeech_vits',
            'facebook/mms-tts-eng',
            'suno/bark'
        ]
        self.base_url = "https://api-inference.huggingface.co/models"
        
        # Debug logging
        logger.info(f"Hugging Face token loaded: {'Yes' if self.api_token and self.api_token.startswith('hf_') else 'No'}")
        
        if not self.api_token or self.api_token == 'hf_your_token_here':
            logger.warning("Hugging Face API token not configured")
            self.api_token = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication"""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers
    
    def _make_request(self, model_name: str, payload: Dict[str, Any], timeout: int = 30) -> Optional[requests.Response]:
        """Make request to Hugging Face Inference API"""
        try:
            url = f"{self.base_url}/{model_name}"
            headers = self._get_headers()
            
            logger.info(f"Making request to Hugging Face: {model_name}")
            logger.debug(f"URL: {url}")
            logger.debug(f"Headers: {headers}")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            logger.info(f"Hugging Face response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Hugging Face API error: {response.text}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error making request to Hugging Face: {e}")
            return None
    
    def rewrite_text(self, text: str, tone: str) -> str:
        """
        Rewrite text using Hugging Face model with specified tone
        """
        if not self.api_token:
            logger.info("Using mock rewriting (no Hugging Face token)")
            return f"[{tone.upper()} TONE] {text}"
        
        try:
            # Tone-specific prompts for text rewriting
            tone_prompts = {
                'neutral': "Rewrite this text in a clear, professional tone:",
                'suspenseful': "Rewrite this text to create suspense and drama:",
                'inspiring': "Rewrite this text in an uplifting, motivational tone:",
                'cheerful': "Rewrite this text in a bright, happy tone:",
                'sad': "Rewrite this text in a soft, emotional tone:",
                'angry': "Rewrite this text with intensity and passion:",
                'playful': "Rewrite this text in a fun, lively tone:",
                'calm': "Rewrite this text in a relaxed, peaceful tone:",
                'confident': "Rewrite this text in an assured, authoritative tone:"
            }
            
            prompt_template = tone_prompts.get(tone, tone_prompts['neutral'])
            full_prompt = f"{prompt_template}\n\nText: {text}\n\nRewritten:"
            
            # Use text generation format for FLAN-T5
            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "do_sample": True
                }
            }
            
            response = self._make_request(self.text_model, payload)
            
            if response and response.status_code == 200:
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '')
                    # Clean up the response
                    if generated_text:
                        # Remove the original prompt from the response
                        clean_text = generated_text.replace(full_prompt, '').strip()
                        return clean_text if clean_text else f"[{tone.upper()}] {text}"
                    else:
                        return f"[{tone.upper()}] {text}"
                else:
                    logger.error(f"Unexpected response format: {result}")
                    return f"[{tone.upper()}] {text}"
            else:
                error_msg = response.text if response else "No response"
                logger.error(f"Hugging Face text generation failed: {error_msg}")
                return f"[{tone.upper()}] {text}"
                
        except Exception as e:
            logger.error(f"Error in text rewriting: {e}")
            return f"[{tone.upper()}] {text}"
    
    def synthesize_speech(self, text: str, voice: str = "default", tone: str = "neutral") -> Optional[bytes]:
        """
        Generate high-quality speech from text using Hugging Face TTS models with tone support
        """
        if not self.api_token:
            logger.info("Using high-quality local TTS (no Hugging Face token)")
            return self._create_mock_audio(text, voice, tone)
        
        try:
            # Try multiple TTS models for best quality
            for model in self.tts_models:
                try:
                    logger.info(f"Trying TTS model: {model}")
                    
                    # Enhanced payload for better quality
                    payload = {
                        "inputs": text,
                        "options": {
                            "use_cache": False,
                            "wait_for_model": True
                        }
                    }
                    
                    # Use different endpoint for TTS models
                    response = self._make_request(model, payload, timeout=90)
                    
                    if response and response.status_code == 200:
                        # Check if response is audio data
                        content_type = response.headers.get('content-type', '')
                        if 'audio' in content_type or len(response.content) > 1000:  # Audio files are typically large
                            logger.info(f"High-quality TTS successful with {model}: {len(response.content)} bytes")
                            return response.content
                        else:
                            # If it's JSON, the model might not be ready
                            try:
                                result = response.json()
                                if 'error' in result:
                                    logger.warning(f"TTS model {model} error: {result['error']}")
                                elif 'estimated_time' in result:
                                    logger.info(f"Model {model} loading, estimated time: {result['estimated_time']}s")
                            except:
                                pass
                            continue
                    else:
                        error_msg = response.text if response else "No response"
                        logger.warning(f"TTS model {model} failed: {error_msg}")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error with TTS model {model}: {e}")
                    continue
            
            # If all Hugging Face models fail, use high-quality local TTS
            logger.info("All Hugging Face TTS models failed, using high-quality local TTS")
            return self._create_mock_audio(text, voice, tone)
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            logger.info("Using high-quality local TTS fallback")
            return self._create_mock_audio(text, voice, tone)
    
    def _create_mock_audio(self, text: str = None, voice: str = "default", tone: str = "neutral") -> bytes:
        """
        Create high-quality speech audio using pyttsx3 with tone and voice variations
        """
        try:
            import pyttsx3
            import tempfile
            import os
            
            # Initialize the TTS engine with high-quality settings
            engine = pyttsx3.init(driverName='sapi5')  # Use SAPI5 for Windows for better quality
            
            # Enhanced tone-specific speech parameters for better audio quality
            tone_settings = {
                'neutral': {'rate': 160, 'volume': 0.9, 'pitch': 0},
                'cheerful': {'rate': 180, 'volume': 0.95, 'pitch': 5},
                'confident': {'rate': 150, 'volume': 0.95, 'pitch': 0},
                'suspenseful': {'rate': 130, 'volume': 0.8, 'pitch': -5},
                'inspiring': {'rate': 170, 'volume': 0.95, 'pitch': 3},
                'sad': {'rate': 120, 'volume': 0.7, 'pitch': -8},
                'angry': {'rate': 190, 'volume': 1.0, 'pitch': 2},
                'playful': {'rate': 185, 'volume': 0.9, 'pitch': 7},
                'calm': {'rate': 140, 'volume': 0.8, 'pitch': -2},
                'professional': {'rate': 155, 'volume': 0.9, 'pitch': 0},
                'dramatic': {'rate': 135, 'volume': 0.85, 'pitch': -3}
            }
            
            # Get tone settings or use neutral as default
            settings = tone_settings.get(tone.lower(), tone_settings['neutral'])
            
            # Set high-quality properties based on tone
            engine.setProperty('rate', settings['rate'])     # Optimized speech rate
            engine.setProperty('volume', settings['volume']) # Optimized volume
            
            # Get available voices and try to match with voice parameter
            voices = engine.getProperty('voices')
            if voices:
                voice_selected = False
                
                # Enhanced voice mapping for all available Windows voices
                voice_preferences = {
                    'david': {
                        'keywords': ['david', 'male', 'man'],
                        'gender': 'male',
                        'index': 0  # David is typically at index 0
                    },
                    'zira': {
                        'keywords': ['zira', 'female', 'woman'],
                        'gender': 'female',
                        'index': 1  # Zira is typically at index 1
                    },
                    'heera': {
                        'keywords': ['heera', 'female', 'woman'],
                        'gender': 'female',
                        'index': 2  # Heera may be at index 2
                    },
                    'mark': {
                        'keywords': ['mark', 'male', 'man'],
                        'gender': 'male',
                        'index': 3  # Mark may be at index 3
                    },
                    'ravi': {
                        'keywords': ['ravi', 'male', 'man'],
                        'gender': 'male',
                        'index': 4  # Ravi may be at index 4
                    },
                    # Legacy mappings for backward compatibility
                    'lisa': {
                        'keywords': ['zira', 'female', 'woman', 'lisa'],
                        'gender': 'female',
                        'index': 1  # Maps to Zira
                    },
                    'michael': {
                        'keywords': ['david', 'male', 'man', 'michael'],
                        'gender': 'male',
                        'index': 0  # Maps to David
                    },
                    'allison': {
                        'keywords': ['heera', 'female', 'woman', 'allison'],
                        'gender': 'female', 
                        'index': 2  # Maps to Heera
                    }
                }
                
                preferred_voice = voice_preferences.get(voice.lower())
                
                if preferred_voice and len(voices) > preferred_voice['index']:
                    # Use the specific index for reliable voice selection
                    selected_voice = voices[preferred_voice['index']]
                    engine.setProperty('voice', selected_voice.id)
                    voice_selected = True
                    logger.info(f"Selected voice by index {preferred_voice['index']}: {selected_voice.name} for {voice}")
                else:
                    # Fallback to keyword matching if index is out of range
                    if preferred_voice:
                        # First, try to find voices with specific keywords
                        for voice_obj in voices:
                            voice_name = voice_obj.name.lower()
                            voice_id = voice_obj.id.lower()
                            
                            # Check if voice name/id contains any of the preferred keywords
                            for keyword in preferred_voice['keywords']:
                                if keyword in voice_name or keyword in voice_id:
                                    engine.setProperty('voice', voice_obj.id)
                                    voice_selected = True
                                    logger.info(f"Selected voice by keyword '{keyword}': {voice_obj.name} for {voice}")
                                    break
                            if voice_selected:
                                break
                        
                        # If no keyword match, try to match by gender
                        if not voice_selected:
                            target_gender = preferred_voice['gender']
                            for voice_obj in voices:
                                voice_name = voice_obj.name.lower()
                                voice_id = voice_obj.id.lower()
                                
                                # Check for gender indicators and specific voice names
                                if target_gender == 'female' and any(indicator in voice_name or indicator in voice_id 
                                                                   for indicator in ['female', 'woman', 'zira', 'heera']):
                                    engine.setProperty('voice', voice_obj.id)
                                    voice_selected = True
                                    logger.info(f"Selected voice by gender '{target_gender}': {voice_obj.name} for {voice}")
                                    break
                                elif target_gender == 'male' and any(indicator in voice_name or indicator in voice_id 
                                                                   for indicator in ['male', 'man', 'david', 'mark', 'ravi']):
                                    engine.setProperty('voice', voice_obj.id)
                                    voice_selected = True
                                    logger.info(f"Selected voice by gender '{target_gender}': {voice_obj.name} for {voice}")
                                    break
                
                # If still no voice selected, cycle through available voices based on voice parameter
                if not voice_selected and voices:
                    # Use different voices for different selections
                    voice_index_map = {
                        'lisa': 0,
                        'michael': min(1, len(voices) - 1),
                        'allison': min(2, len(voices) - 1) if len(voices) > 2 else 0
                    }
                    
                    voice_index = voice_index_map.get(voice.lower(), 0)
                    selected_voice = voices[voice_index]
                    engine.setProperty('voice', selected_voice.id)
                    voice_selected = True
                    logger.info(f"Selected voice by index {voice_index}: {selected_voice.name} for {voice}")
                
                # Log available voices for debugging
                logger.info(f"Available voices on system:")
                for i, v in enumerate(voices):
                    logger.info(f"  {i}: {v.name} (ID: {v.id})")
                
                if not voice_selected:
                    # Fallback to first available voice
                    engine.setProperty('voice', voices[0].id)
                    logger.info(f"Using fallback voice: {voices[0].name}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_path = temp_file.name
            
            # Generate speech and save to temporary file
            engine.save_to_file(text or "Hello, this is a test message.", temp_path)
            engine.runAndWait()
            
            # Read the generated audio file
            try:
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # Clean up temporary file
                os.unlink(temp_path)
                
                logger.info(f"Generated {len(audio_data)} bytes of audio with voice: {voice}, tone: {tone}")
                return audio_data
                
            except Exception as e:
                logger.error(f"Error reading generated audio file: {e}")
                # Clean up on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return b""  # Return empty bytes on error
                
        except ImportError:
            logger.error("pyttsx3 not available, cannot generate speech")
            return b""
        except Exception as e:
            logger.error(f"Error in mock TTS generation: {e}")
            return b""
            return self._create_silence_wav()
    
    def _create_silence_wav(self) -> bytes:
        """
        Create a simple WAV file with silence as final fallback
        """
        import wave
        import struct
        import io
        
        # Create a simple 2-second silence WAV file
        sample_rate = 22050
        duration = 2  # seconds
        num_samples = int(sample_rate * duration)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            # Write silence (zeros)
            for _ in range(num_samples):
                wav_file.writeframes(struct.pack('<h', 0))
        
        wav_buffer.seek(0)
        return wav_buffer.getvalue()
    
    def get_available_models(self) -> Dict[str, list]:
        """Get list of available models (for information)"""
        return {
            "text_models": [
                "ibm-granite/granite-3.3-8b-instruct",
                "ibm-granite/granite-speech-3.3-8b", 
                "ibm-granite/granite-speech-3.3-2b"
            ],
            "tts_models": [
                "microsoft/speecht5_tts",
                "facebook/fastspeech2-en-ljspeech",
                "espnet/kan-bayashi_ljspeech_vits"
            ]
        }
    
    def test_connection(self) -> Dict[str, bool]:
        """Test connection to Hugging Face services"""
        results = {
            "text_generation": False,
            "text_to_speech": False,
            "api_token_valid": bool(self.api_token)
        }
        
        if not self.api_token:
            return results
        
        # Test text generation
        try:
            test_response = self.rewrite_text("Hello, this is a test.", "neutral")
            results["text_generation"] = bool(test_response and test_response != "Hello, this is a test.")
        except:
            pass
        
        # Test TTS
        try:
            test_audio = self.synthesize_speech("Test", "default", "neutral")
            results["text_to_speech"] = bool(test_audio)
        except:
            pass
        
        return results

# Global instance
hf_service = HuggingFaceService()
