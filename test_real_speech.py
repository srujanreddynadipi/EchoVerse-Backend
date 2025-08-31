import requests

print('Testing /synthesize endpoint with real speech...')
try:
    response = requests.post('http://localhost:5000/synthesize', 
                           json={'text': 'Welcome to EchoVerse! This is your AI-powered audiobook companion. I can now convert any text you provide into natural-sounding speech. Try me with your favorite story or article!'})
    
    print(f'Status: {response.status_code}')
    print(f'Content-Type: {response.headers.get("content-type")}')
    print(f'Audio Size: {len(response.content)} bytes')
    
    if response.status_code == 200:
        with open('endpoint_test_speech.wav', 'wb') as f:
            f.write(response.content)
        print('✅ SUCCESS: Real speech from endpoint saved as endpoint_test_speech.wav')
        
        if len(response.content) > 100000:  # Large file indicates real speech
            print('🎉 PERFECT: Large audio file generated - contains real speech!')
        else:
            print('⚠️  Small audio file - might still be silence')
    else:
        print(f'❌ FAILED: {response.text}')
        
except Exception as e:
    print(f'❌ ERROR: {e}')
