#!/usr/bin/env python3
"""
Hugging Face API Test Script for EchoVerse
Run this script to test your Hugging Face API credentials and models
"""

import os
import sys
from dotenv import load_dotenv
from huggingface_service import hf_service

# Load environment variables
load_dotenv()

def test_huggingface_setup():
    """Test Hugging Face setup and credentials"""
    print("🤗 EchoVerse Hugging Face API Test Suite")
    print("=" * 50)
    
    # Check environment variables
    api_token = os.getenv('HUGGINGFACE_API_TOKEN')
    text_model = os.getenv('HUGGINGFACE_TEXT_MODEL', 'ibm-granite/granite-3.3-8b-instruct')
    tts_model = os.getenv('HUGGINGFACE_TTS_MODEL', 'microsoft/speecht5_tts')
    
    print(f"📁 Environment Configuration:")
    print(f"   API Token: {'✅ Configured' if api_token and api_token != 'hf_your_token_here' else '❌ Not configured'}")
    print(f"   Text Model: {text_model}")
    print(f"   TTS Model: {tts_model}")
    print()
    
    if not api_token or api_token == 'hf_your_token_here':
        print("❌ Hugging Face API token not found!")
        print("📝 Please set your HUGGINGFACE_API_TOKEN in the .env file")
        print("💡 Get your token from: https://huggingface.co/settings/tokens")
        return False
    
    # Test connection
    print("🔗 Testing Hugging Face API Connection...")
    test_results = hf_service.test_connection()
    
    print(f"   API Token Valid: {'✅ YES' if test_results['api_token_valid'] else '❌ NO'}")
    print(f"   Text Generation: {'✅ WORKING' if test_results['text_generation'] else '❌ FAILED'}")
    print(f"   Text-to-Speech: {'✅ WORKING' if test_results['text_to_speech'] else '❌ FAILED'}")
    print()
    
    # Test text rewriting with different tones
    if test_results['text_generation']:
        print("📝 Testing Text Rewriting with IBM Granite...")
        test_text = "Hello, this is a simple test message."
        
        tones_to_test = ['cheerful', 'inspiring', 'calm']
        for tone in tones_to_test:
            try:
                result = hf_service.rewrite_text(test_text, tone)
                print(f"   {tone.capitalize()}: {result[:60]}...")
            except Exception as e:
                print(f"   {tone.capitalize()}: ❌ Error - {str(e)}")
        print()
    
    # Test TTS
    if test_results['text_to_speech']:
        print("🎵 Testing Text-to-Speech...")
        try:
            audio_data = hf_service.synthesize_speech("Hello from EchoVerse!", "default")
            if audio_data:
                # Save test audio
                with open('test_huggingface_audio.wav', 'wb') as f:
                    f.write(audio_data)
                print("   ✅ TTS test successful - saved as 'test_huggingface_audio.wav'")
            else:
                print("   ❌ TTS test failed - no audio data returned")
        except Exception as e:
            print(f"   ❌ TTS test error: {str(e)}")
        print()
    
    # Show available models
    print("📚 Available Models:")
    models = hf_service.get_available_models()
    print("   Text Generation Models:")
    for model in models['text_models']:
        print(f"     - {model}")
    print("   Text-to-Speech Models:")
    for model in models['tts_models']:
        print(f"     - {model}")
    print()
    
    # Summary
    all_working = all([
        test_results['api_token_valid'],
        test_results['text_generation'],
        test_results['text_to_speech']
    ])
    
    print("=" * 50)
    print("📊 Test Results Summary:")
    if all_working:
        print("🎉 All tests passed! Your Hugging Face setup is ready!")
        print("🚀 EchoVerse will use IBM Granite models for text rewriting")
        print("🎵 High-quality TTS will be available for audio generation")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        print("💡 EchoVerse will still work with fallback/mock responses")
    
    print()
    print("🔗 Useful Links:")
    print("   - Get API Token: https://huggingface.co/settings/tokens")
    print("   - IBM Granite Models: https://huggingface.co/ibm-granite")
    print("   - Hugging Face Documentation: https://huggingface.co/docs")
    
    return all_working

def main():
    """Main test function"""
    try:
        success = test_huggingface_setup()
        if success:
            print("\n✅ Ready to start EchoVerse with Hugging Face AI!")
        else:
            print("\n⚠️  Fix the issues above and run this test again")
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    main()
