#!/usr/bin/env python3
"""
IBM Watson Credentials Test Script for EchoVerse
Run this script to test your IBM Watson API credentials
"""

import os
import sys
import requests
import json
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_tts_service():
    """Test IBM Watson Text-to-Speech service"""
    print("🎵 Testing Text-to-Speech Service...")
    
    api_key = os.getenv('TTS_API_KEY')
    service_url = os.getenv('TTS_URL')
    
    if not api_key or not service_url:
        print("❌ TTS credentials not found in .env file")
        return False
    
    try:
        # Initialize authenticator and service
        authenticator = IAMAuthenticator(api_key)
        tts = TextToSpeechV1(authenticator=authenticator)
        tts.set_service_url(service_url)
        
        # Test with a simple phrase
        response = tts.synthesize(
            text='Hello from EchoVerse! Your Text-to-Speech service is working correctly.',
            voice='en-US_LisaV3Voice',
            accept='audio/mp3'
        )
        
        if response.status_code == 200:
            print("✅ TTS Service: SUCCESS")
            print(f"   API Key: {api_key[:8]}...")
            print(f"   Service URL: {service_url}")
            
            # Save test audio file
            with open('test_tts_output.mp3', 'wb') as audio_file:
                audio_file.write(response.get_result().content)
            print("   Test audio saved as 'test_tts_output.mp3'")
            return True
        else:
            print(f"❌ TTS Service failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ TTS Service error: {str(e)}")
        return False

def get_watson_access_token():
    """Get access token for Watsonx.ai"""
    api_key = os.getenv('WATSONX_API_KEY')
    
    if not api_key:
        return None
    
    try:
        response = requests.post(
            'https://iam.cloud.ibm.com/identity/token',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'urn:iam:params:oauth:grant-type:apikey',
                'apikey': api_key
            }
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            print(f"❌ Failed to get access token: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Access token error: {str(e)}")
        return None

def test_watsonx_service():
    """Test IBM Watsonx.ai service"""
    print("\n🤖 Testing Watsonx.ai Service...")
    
    api_key = os.getenv('WATSONX_API_KEY')
    base_url = os.getenv('WATSONX_URL')
    project_id = os.getenv('WATSONX_PROJECT_ID')
    
    if not all([api_key, base_url, project_id]):
        print("❌ Watsonx credentials not found in .env file")
        return False
    
    # Get access token
    access_token = get_watson_access_token()
    if not access_token:
        return False
    
    try:
        # Test text generation
        url = f"{base_url}/ml/v1/text/generation"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = {
            "input": "Rewrite this text in a cheerful tone: Hello, this is a test message.",
            "model_id": "ibm/granite-13b-chat-v2",
            "project_id": project_id,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 100,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('results', [{}])[0].get('generated_text', '')
            
            print("✅ Watsonx Service: SUCCESS")
            print(f"   API Key: {api_key[:8]}...")
            print(f"   Project ID: {project_id}")
            print(f"   Generated text: {generated_text[:100]}...")
            return True
        else:
            print(f"❌ Watsonx Service failed with status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Watsonx Service error: {str(e)}")
        return False

def test_available_voices():
    """Test and display available TTS voices"""
    print("\n🎤 Testing Available Voices...")
    
    api_key = os.getenv('TTS_API_KEY')
    service_url = os.getenv('TTS_URL')
    
    if not api_key or not service_url:
        print("❌ TTS credentials not available")
        return False
    
    try:
        authenticator = IAMAuthenticator(api_key)
        tts = TextToSpeechV1(authenticator=authenticator)
        tts.set_service_url(service_url)
        
        voices = tts.list_voices().get_result()
        
        print("✅ Available Voices:")
        for voice in voices['voices']:
            if 'en-US' in voice['name']:  # Filter for English voices
                print(f"   - {voice['name']}: {voice['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing voices: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 EchoVerse IBM Watson API Test Suite")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("📝 Please create a .env file with your IBM Watson credentials")
        print("💡 See IBM_WATSON_SETUP_GUIDE.md for detailed instructions")
        return
    
    print("📁 Environment file found")
    
    # Test services
    tts_success = test_tts_service()
    watsonx_success = test_watsonx_service()
    voices_success = test_available_voices()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Text-to-Speech: {'✅ PASS' if tts_success else '❌ FAIL'}")
    print(f"   Watsonx.ai: {'✅ PASS' if watsonx_success else '❌ FAIL'}")
    print(f"   Voice List: {'✅ PASS' if voices_success else '❌ FAIL'}")
    
    if tts_success and watsonx_success:
        print("\n🎉 All tests passed! Your IBM Watson setup is ready for EchoVerse!")
        print("🚀 You can now run the full application with real IBM Watson integration")
    else:
        print("\n⚠️  Some tests failed. Please check your credentials and try again.")
        print("📖 See IBM_WATSON_SETUP_GUIDE.md for troubleshooting help")

if __name__ == "__main__":
    main()
