#!/usr/bin/env python3
"""
Test script to verify database functionality
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager

def test_database():
    """Test database operations"""
    print("🔍 Testing EchoVerse Database...")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Ensure database exists
    print("0. Setting up database...")
    try:
        db_manager.ensure_database_exists()
        print("✅ Database setup completed")
    except Exception as e:
        if "Duplicate key name" in str(e) or "already exists" in str(e):
            print("✅ Database already exists and configured")
        else:
            print(f"❌ Database setup failed: {e}")
            return
    
    # Test 1: Get default user
    print("1. Testing user retrieval...")
    user = db_manager.get_user_by_email("sruja.reddy@student.edu")
    if user:
        print(f"✅ User found: {user['name']}")
        print(f"   📧 Email: {user['email']}")
        print(f"   🏫 University: {user['university']}")
        print(f"   📚 Course: {user['course']}")
        print(f"   🎯 GPA: {user['gpa']}")
        print(f"   💻 Skills: {', '.join(user['skills'][:3])}...")
        print(f"   ⭐ Interests: {', '.join(user['interests'][:3])}...")
    else:
        print("❌ Default user not found")
        return False
    
    print()
    
    # Test 2: Get user history
    print("2. Testing audio history...")
    history = db_manager.get_user_audio_history(user['id'], limit=5)
    print(f"✅ Found {len(history)} history items")
    for i, item in enumerate(history, 1):
        print(f"   {i}. {item['tone'].title()} tone - {item['voice'].title()} voice")
        print(f"      📝 Text: {item['original_text'][:50]}...")
        print(f"      🎵 Audio: {'Generated' if item['audio_generated'] else 'Not generated'}")
    
    print()
    
    # Test 3: Get tones and voices
    print("3. Testing configuration data...")
    tones = db_manager.get_tones()
    voices = db_manager.get_voices()
    
    print(f"✅ Available tones ({len(tones)}):")
    for tone in tones[:5]:  # Show first 5
        print(f"   - {tone['tone_name']}: {tone['description']}")
    
    print(f"✅ Available voices ({len(voices)}):")
    for voice in voices:
        print(f"   - {voice['voice_name']}: {voice['description']}")
    
    print()
    
    # Test 4: Create a test history entry
    print("4. Testing history creation...")
    history_id = db_manager.create_audio_history(
        user_id=user['id'],
        original_text="This is a test message for database verification.",
        rewritten_text="[NEUTRAL TONE] This is a test message for database verification.",
        tone='neutral',
        voice='allison',
        audio_generated=False
    )
    
    if history_id:
        print(f"✅ Test history entry created with ID: {history_id}")
        
        # Clean up - delete the test entry
        db_manager.delete_audio_history(history_id, user['id'])
        print("🧹 Test entry cleaned up")
    else:
        print("❌ Failed to create test history entry")
        return False
    
    print()
    print("🎉 All database tests passed successfully!")
    print("🚀 Database is ready for EchoVerse application!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_database()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        sys.exit(1)
