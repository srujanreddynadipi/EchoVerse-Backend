import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('HUGGINGFACE_API_TOKEN')

# Test different TTS models that might work
models_to_test = [
    'facebook/mms-tts-eng',
    'microsoft/speecht5_tts', 
    'suno/bark-small',
    'facebook/fastspeech2-en-ljspeech'
]

headers = {'Authorization': f'Bearer {token}'}

print('Testing available TTS models...')
for model in models_to_test:
    try:
        url = f'https://api-inference.huggingface.co/models/{model}'
        response = requests.post(url, 
                               headers=headers,
                               json={'inputs': 'Hello world'},
                               timeout=15)
        print(f'{model}: Status {response.status_code}')
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'unknown')
            size = len(response.content)
            print(f'  ✅ Working! Content-Type: {content_type}, Size: {size} bytes')
            if size > 1000:
                # Save a sample
                with open(f'test_{model.replace("/", "_")}.wav', 'wb') as f:
                    f.write(response.content)
                print(f'  Saved sample audio')
        else:
            error_text = response.text[:100] if response.text else "No error message"
            print(f'  ❌ Error: {error_text}')
    except Exception as e:
        print(f'{model}: ❌ Exception: {e}')
    print()
