#!/usr/bin/env python3
"""
Interactive IBM Watson Credentials Setup for EchoVerse
This script helps you configure your IBM Watson API credentials
"""

import os
import sys
import re

def print_header():
    """Print setup header"""
    print("=" * 60)
    print("🚀 EchoVerse IBM Watson Credentials Setup")
    print("=" * 60)
    print()

def print_step(step, title):
    """Print step header"""
    print(f"📍 Step {step}: {title}")
    print("-" * 40)

def validate_api_key(api_key):
    """Validate API key format"""
    if not api_key or len(api_key) < 10:
        return False
    return True

def validate_url(url):
    """Validate URL format"""
    url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    return url_pattern.match(url) is not None

def validate_project_id(project_id):
    """Validate project ID format"""
    if not project_id or len(project_id) < 10:
        return False
    return True

def get_user_input(prompt, validator=None, required=True):
    """Get and validate user input"""
    while True:
        value = input(prompt).strip()
        
        if not value and not required:
            return ""
        
        if not value and required:
            print("❌ This field is required. Please try again.")
            continue
            
        if validator and not validator(value):
            print("❌ Invalid format. Please try again.")
            continue
            
        return value

def setup_tts_credentials():
    """Setup Text-to-Speech credentials"""
    print_step(1, "Text-to-Speech Service Setup")
    
    print("🎵 First, let's set up your IBM Watson Text-to-Speech service.")
    print()
    print("To get your TTS credentials:")
    print("1. Go to https://cloud.ibm.com")
    print("2. Create or access your Text-to-Speech service")
    print("3. Go to 'Service credentials' and copy your API key and URL")
    print()
    
    tts_api_key = get_user_input(
        "Enter your TTS API Key: ",
        validator=validate_api_key
    )
    
    print("\nDefault TTS URL: https://api.us-south.text-to-speech.watson.cloud.ibm.com")
    use_default_url = input("Use default TTS URL? (y/n): ").lower().startswith('y')
    
    if use_default_url:
        tts_url = "https://api.us-south.text-to-speech.watson.cloud.ibm.com"
    else:
        tts_url = get_user_input(
            "Enter your TTS URL: ",
            validator=validate_url
        )
    
    return tts_api_key, tts_url

def setup_watsonx_credentials():
    """Setup Watsonx.ai credentials"""
    print_step(2, "Watsonx.ai Service Setup")
    
    print("🤖 Now, let's set up your IBM Watsonx.ai service.")
    print()
    print("To get your Watsonx credentials:")
    print("1. Go to https://cloud.ibm.com")
    print("2. Create or access your Watsonx.ai service")
    print("3. Create an API key in IAM")
    print("4. Get your Project ID from your Watsonx project")
    print()
    
    watsonx_api_key = get_user_input(
        "Enter your Watsonx API Key: ",
        validator=validate_api_key
    )
    
    print("\nDefault Watsonx URL: https://us-south.ml.cloud.ibm.com")
    use_default_url = input("Use default Watsonx URL? (y/n): ").lower().startswith('y')
    
    if use_default_url:
        watsonx_url = "https://us-south.ml.cloud.ibm.com"
    else:
        watsonx_url = get_user_input(
            "Enter your Watsonx URL: ",
            validator=validate_url
        )
    
    watsonx_project_id = get_user_input(
        "Enter your Watsonx Project ID: ",
        validator=validate_project_id
    )
    
    return watsonx_api_key, watsonx_url, watsonx_project_id

def update_env_file(credentials):
    """Update .env file with new credentials"""
    env_path = '.env'
    
    # Read current .env file
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add credentials
    updated_lines = []
    keys_to_update = {
        'TTS_API_KEY': credentials['tts_api_key'],
        'TTS_URL': credentials['tts_url'],
        'WATSONX_API_KEY': credentials['watsonx_api_key'],
        'WATSONX_URL': credentials['watsonx_url'],
        'WATSONX_PROJECT_ID': credentials['watsonx_project_id']
    }
    
    keys_found = set()
    
    for line in env_lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0].strip()
            if key in keys_to_update:
                updated_lines.append(f"{key}={keys_to_update[key]}\n")
                keys_found.add(key)
            else:
                updated_lines.append(line + '\n')
        else:
            updated_lines.append(line + '\n')
    
    # Add any missing keys
    for key, value in keys_to_update.items():
        if key not in keys_found:
            updated_lines.append(f"{key}={value}\n")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)

def test_credentials():
    """Offer to test the credentials"""
    print_step(3, "Test Your Setup")
    
    print("🧪 Would you like to test your IBM Watson credentials?")
    test_now = input("Run credential test? (y/n): ").lower().startswith('y')
    
    if test_now:
        print("\n🔍 Running credential tests...")
        os.system('python test_watson_credentials.py')
    else:
        print("\n💡 You can test your credentials later by running:")
        print("   python test_watson_credentials.py")

def main():
    """Main setup function"""
    print_header()
    
    print("This script will help you configure IBM Watson credentials for EchoVerse.")
    print("Make sure you have:")
    print("✓ IBM Cloud account")
    print("✓ Text-to-Speech service created")
    print("✓ Watsonx.ai service created")
    print()
    
    proceed = input("Ready to proceed? (y/n): ").lower().startswith('y')
    if not proceed:
        print("Setup cancelled. Run this script again when you're ready!")
        return
    
    print()
    
    try:
        # Setup TTS credentials
        tts_api_key, tts_url = setup_tts_credentials()
        print("✅ TTS credentials configured")
        print()
        
        # Setup Watsonx credentials
        watsonx_api_key, watsonx_url, watsonx_project_id = setup_watsonx_credentials()
        print("✅ Watsonx credentials configured")
        print()
        
        # Prepare credentials dictionary
        credentials = {
            'tts_api_key': tts_api_key,
            'tts_url': tts_url,
            'watsonx_api_key': watsonx_api_key,
            'watsonx_url': watsonx_url,
            'watsonx_project_id': watsonx_project_id
        }
        
        # Update .env file
        print("💾 Updating .env file...")
        update_env_file(credentials)
        print("✅ Credentials saved to .env file")
        print()
        
        # Test credentials
        test_credentials()
        
        print()
        print("🎉 Setup Complete!")
        print("=" * 60)
        print("Your IBM Watson credentials have been configured.")
        print("You can now run EchoVerse with real AI-powered features!")
        print()
        print("Next steps:")
        print("1. Start the backend: python app.py")
        print("2. Start the frontend: npm start")
        print("3. Create amazing AI-powered audiobooks! 🚀")
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        print("Please check your credentials and try again")

if __name__ == "__main__":
    main()
