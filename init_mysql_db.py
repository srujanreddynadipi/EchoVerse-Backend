"""
MySQL Database Initialization Script for EchoVerse
This script creates the database and initializes it with sample data.
"""

import os
import sys
import pymysql
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager

# Load environment variables
load_dotenv()

def init_mysql_database():
    """Initialize MySQL database with schema and sample data"""
    print("Initializing MySQL database for EchoVerse...")
    
    try:
        # Create database manager instance
        db_manager = DatabaseManager()
        
        # Ensure database and tables exist
        print("Creating database and tables...")
        db_manager.ensure_database_exists()
        
        # Test connection
        print("Testing database connection...")
        if not db_manager.test_connection():
            raise Exception("Database connection test failed")
        
        print("✅ Database connection successful!")
        
        # Create a sample user
        print("Creating sample user...")
        user_id = db_manager.create_user(
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-0123",
            location="New York, USA",
            university="Example University",
            course="Computer Science",
            year="3rd Year",
            roll_number="CS2021001",
            gpa=3.85,
            bio="Computer Science student passionate about AI and machine learning."
        )
        
        if user_id:
            print(f"✅ Sample user created with ID: {user_id}")
            
            # Add sample skills
            skills = ["Python", "JavaScript", "React", "Machine Learning", "Data Analysis"]
            for skill in skills:
                db_manager.add_user_skill(user_id, skill)
            print("✅ Sample skills added")
            
            # Add sample interests
            interests = ["Artificial Intelligence", "Web Development", "Data Science", "Robotics"]
            for interest in interests:
                db_manager.add_user_interest(user_id, interest)
            print("✅ Sample interests added")
            
            # Add sample achievements
            achievements = [
                ("Dean's List - Fall 2023", "2023-12-15"),
                ("Hackathon Winner - Tech Fest 2023", "2023-11-20"),
                ("Research Paper Published", "2023-10-10")
            ]
            for achievement_text, date in achievements:
                db_manager.add_user_achievement(user_id, achievement_text, date)
            print("✅ Sample achievements added")
            
            # Add sample projects
            projects = [
                {
                    "project_name": "EchoVerse AI Audiobook",
                    "description": "AI-powered text-to-speech application with emotional tone control",
                    "technologies": "Python, Flask, React, IBM Watson",
                    "project_url": "https://github.com/johndoe/echoverse"
                },
                {
                    "project_name": "Weather Prediction Model",
                    "description": "Machine learning model for weather forecasting using historical data",
                    "technologies": "Python, TensorFlow, Pandas, Scikit-learn",
                    "project_url": "https://github.com/johndoe/weather-ml"
                }
            ]
            for project in projects:
                db_manager.add_user_project(user_id, **project)
            print("✅ Sample projects added")
            
            # Add sample audio history
            history_id = db_manager.save_audio_history(
                user_id=user_id,
                original_text="Hello, this is a test of the EchoVerse system.",
                rewritten_text="Welcome! This is an exciting demonstration of the EchoVerse platform.",
                tone="inspiring",
                voice="lisa",
                audio_file_path="/audio/sample_audio_001.wav"
            )
            if history_id:
                db_manager.update_audio_history_status(history_id, "completed")
            print("✅ Sample audio history added")
        
        # Get and display database statistics
        print("\n📊 Database Statistics:")
        stats = db_manager.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n🎉 MySQL database initialization completed successfully!")
        print(f"Database: {os.getenv('DB_DATABASE')}")
        print(f"Host: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_mysql_database()
