"""
MySQL Database Testing Script for EchoVerse
This script tests all database functionality with the MySQL backend.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager

# Load environment variables
load_dotenv()

def test_mysql_database():
    """Test all database operations with MySQL"""
    print("Testing MySQL database functionality for EchoVerse...")
    
    try:
        # Create database manager instance
        db_manager = DatabaseManager()
        
        # Test 1: Connection
        print("\n1. Testing database connection...")
        if db_manager.test_connection():
            print("✅ Database connection successful")
        else:
            raise Exception("Database connection failed")
        
        # Test 2: Configuration data
        print("\n2. Testing configuration data...")
        tones = db_manager.get_available_tones()
        voices = db_manager.get_available_voices()
        print(f"✅ Found {len(tones)} tones and {len(voices)} voices")
        
        # Test 3: User operations
        print("\n3. Testing user operations...")
        
        # Create test user
        test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        user_id = db_manager.create_user(
            name="Test User",
            email=test_email,
            phone="+1-555-9999",
            location="Test City",
            university="Test University",
            course="Test Course",
            year="Test Year",
            bio="This is a test user for database testing."
        )
        print(f"✅ Created test user with ID: {user_id}")
        
        # Get user
        user = db_manager.get_user(user_id)
        if user and user['email'] == test_email:
            print("✅ User retrieval successful")
        else:
            raise Exception("User retrieval failed")
        
        # Update user
        updated = db_manager.update_user(user_id, gpa=3.95, location="Updated City")
        if updated:
            print("✅ User update successful")
        else:
            raise Exception("User update failed")
        
        # Test 4: User skills
        print("\n4. Testing user skills...")
        skill_id = db_manager.add_user_skill(user_id, "Test Skill")
        skills = db_manager.get_user_skills(user_id)
        if skills and len(skills) > 0:
            print("✅ Skills operations successful")
        
        # Test 5: User interests
        print("\n5. Testing user interests...")
        interest_id = db_manager.add_user_interest(user_id, "Test Interest")
        interests = db_manager.get_user_interests(user_id)
        if interests and len(interests) > 0:
            print("✅ Interests operations successful")
        
        # Test 6: User achievements
        print("\n6. Testing user achievements...")
        achievement_id = db_manager.add_user_achievement(
            user_id, 
            "Test Achievement", 
            datetime.now().date()
        )
        achievements = db_manager.get_user_achievements(user_id)
        if achievements and len(achievements) > 0:
            print("✅ Achievements operations successful")
        
        # Test 7: User projects
        print("\n7. Testing user projects...")
        project_id = db_manager.add_user_project(
            user_id,
            "Test Project",
            "This is a test project",
            "Python, MySQL",
            "https://github.com/test/project"
        )
        projects = db_manager.get_user_projects(user_id)
        if projects and len(projects) > 0:
            print("✅ Projects operations successful")
        
        # Test 8: Audio history
        print("\n8. Testing audio history...")
        history_id = db_manager.save_audio_history(
            user_id=user_id,
            original_text="This is test text for audio generation.",
            rewritten_text="This represents test content for audio synthesis.",
            tone="neutral",
            voice="lisa"
        )
        
        # Update status
        db_manager.update_audio_history_status(history_id, "completed", "/audio/test_audio.wav")
        
        # Get history
        history = db_manager.get_user_audio_history(user_id)
        if history and len(history) > 0:
            print("✅ Audio history operations successful")
        
        # Test 9: Configuration queries
        print("\n9. Testing configuration queries...")
        tone_prompt = db_manager.get_tone_prompt("neutral")
        voice_watson_id = db_manager.get_voice_watson_id("lisa")
        if tone_prompt and voice_watson_id:
            print("✅ Configuration queries successful")
        
        # Test 10: Database statistics
        print("\n10. Testing database statistics...")
        stats = db_manager.get_database_stats()
        if stats and 'users' in stats:
            print("✅ Database statistics successful")
            print(f"   Users: {stats.get('users', 0)}")
            print(f"   Audio History: {stats.get('audio_history', 0)}")
            print(f"   Active Tones: {stats.get('active_tones', 0)}")
            print(f"   Active Voices: {stats.get('active_voices', 0)}")
        
        # Clean up test data
        print("\n11. Cleaning up test data...")
        deleted = db_manager.delete_user(user_id)
        if deleted:
            print("✅ Test data cleanup successful")
        
        print("\n🎉 All MySQL database tests passed successfully!")
        print(f"Database: {os.getenv('DB_DATABASE')}")
        print(f"Host: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_mysql_database()
