#!/usr/bin/env python3
"""
Interactive Hugging Face Setup for EchoVerse
This script helps you configure Hugging Face API credentials
"""

import os
import re

def print_header():
    """Print setup header"""
    print("=" * 60)
    print("🤗 EchoVerse Hugging Face API Setup")
    print("=" * 60)
    print()

def get_huggingface_token():
    """Get Hugging Face API token from user"""
    print("📍 Step 1: Get Your Hugging Face API Token")
    print("-" * 40)
    print("To get your Hugging Face API token:")
    print("1. Go to https://huggingface.co")
    print("2. Sign up/login to your account")
    print("3. Go to Settings → Access Tokens")
    print("4. Click 'New token' → Select 'Read' access")
    print("5. Copy the token (starts with 'hf_')")
    print()
    
    while True:
        token = input("Enter your Hugging Face API token: ").strip()
        
        if not token:
            print("❌ Token is required. Please try again.")
            continue
            
        if not token.startswith('hf_'):
            print("❌ Invalid token format. Token should start with 'hf_'")
            continue
            
        if len(token) < 20:
            print("❌ Token seems too short. Please check and try again.")
            continue
            
        return token

def select_models():
    """Let user select models"""
    print("\n📍 Step 2: Select AI Models")
    print("-" * 40)
    
    print("🤖 Text Generation Models (IBM Granite):")
    text_models = [
        "ibm-granite/granite-3.3-8b-instruct",
        "ibm-granite/granite-speech-3.3-8b", 
        "ibm-granite/granite-speech-3.3-2b"
    ]
    
    for i, model in enumerate(text_models, 1):
        print(f"{i}. {model}")
    
    print("\nRecommended: granite-3.3-8b-instruct (best for text rewriting)")
    choice = input("\nSelect text model (1-3) or press Enter for default: ").strip()
    
    if choice in ['1', '2', '3']:
        text_model = text_models[int(choice) - 1]
    else:
        text_model = text_models[0]  # Default
    
    print(f"✅ Selected: {text_model}")
    
    print("\n🎵 Text-to-Speech Models:")
    tts_models = [
        "microsoft/speecht5_tts",
        "facebook/fastspeech2-en-ljspeech", 
        "espnet/kan-bayashi_ljspeech_vits"
    ]
    
    for i, model in enumerate(tts_models, 1):
        print(f"{i}. {model}")
    
    print("\nRecommended: microsoft/speecht5_tts (best quality)")
    choice = input("\nSelect TTS model (1-3) or press Enter for default: ").strip()
    
    if choice in ['1', '2', '3']:
        tts_model = tts_models[int(choice) - 1]
    else:
        tts_model = tts_models[0]  # Default
    
    print(f"✅ Selected: {tts_model}")
    
    return text_model, tts_model

def update_env_file(token, text_model, tts_model):
    """Update .env file with Hugging Face configuration"""
    env_path = '.env'
    
    # Read current .env file
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Configuration to update
    hf_config = {
        'HUGGINGFACE_API_TOKEN': token,
        'HUGGINGFACE_TEXT_MODEL': text_model,
        'HUGGINGFACE_TTS_MODEL': tts_model
    }
    
    # Update or add Hugging Face configuration
    updated_lines = []
    keys_found = set()
    
    for line in env_lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0].strip()
            if key in hf_config:
                updated_lines.append(f"{key}={hf_config[key]}\n")
                keys_found.add(key)
            else:
                updated_lines.append(line + '\n')
        else:
            updated_lines.append(line + '\n')
    
    # Add any missing Hugging Face keys
    for key, value in hf_config.items():
        if key not in keys_found:
            updated_lines.append(f"{key}={value}\n")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)

def test_setup():
    """Offer to test the setup"""
    print("\n📍 Step 3: Test Your Setup")
    print("-" * 40)
    
    test_now = input("Would you like to test your Hugging Face setup now? (y/n): ").lower().startswith('y')
    
    if test_now:
        print("\n🧪 Running Hugging Face tests...")
        os.system('python test_huggingface_setup.py')
    else:
        print("\n💡 You can test your setup later by running:")
        print("   python test_huggingface_setup.py")

def main():
    """Main setup function"""
    print_header()
    
    print("This script will configure Hugging Face APIs for EchoVerse.")
    print("You'll get access to:")
    print("✨ IBM Granite models for intelligent text rewriting")
    print("🎵 High-quality text-to-speech generation")
    print("🆓 Generous free tier (no credit card required)")
    print()
    
    proceed = input("Ready to proceed? (y/n): ").lower().startswith('y')
    if not proceed:
        print("Setup cancelled. Run this script again when you're ready!")
        return
    
    try:
        # Get API token
        token = get_huggingface_token()
        
        # Select models
        text_model, tts_model = select_models()
        
        # Update .env file
        print("\n💾 Updating configuration...")
        update_env_file(token, text_model, tts_model)
        print("✅ Configuration saved to .env file")
        
        # Test setup
        test_setup()
        
        print("\n🎉 Hugging Face Setup Complete!")
        print("=" * 60)
        print("Your EchoVerse app is now configured with:")
        print(f"📝 Text Model: {text_model}")
        print(f"🎵 TTS Model: {tts_model}")
        print()
        print("🚀 Next Steps:")
        print("1. Start the backend: python app.py")
        print("2. Start the frontend: npm start")
        print("3. Create AI-powered audiobooks with IBM Granite!")
        print()
        print("💡 Benefits over IBM Watson:")
        print("   ✓ Easier setup (just API token)")
        print("   ✓ No complex IBM Cloud configuration")
        print("   ✓ Access to latest IBM Granite models")
        print("   ✓ Generous free tier")
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        print("Please check your internet connection and try again")

if __name__ == "__main__":
    main()
