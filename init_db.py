#!/usr/bin/env python3
"""
Database initialization script for EchoVerse
This script sets up the database with initial data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize the database with default data"""
    try:
        logger.info("Initializing EchoVerse database...")
        
        # Database is automatically created by the DatabaseManager
        # Let's add a default user for testing
        default_user_email = "sruja.reddy@student.edu"
        
        # Check if default user exists
        existing_user = db_manager.get_user_by_email(default_user_email)
        
        if not existing_user:
            logger.info("Creating default user...")
            default_user_data = {
                'name': 'Sruja Reddy',
                'email': default_user_email,
                'phone': '+1 (555) 123-4567',
                'location': 'Hyderabad, India',
                'date_of_birth': '2002-05-15',
                'university': 'JNTU Hyderabad',
                'course': 'Computer Science Engineering',
                'year': '3rd Year',
                'roll_number': 'CSE2021001',
                'gpa': 8.7,
                'bio': 'Passionate computer science student with a keen interest in artificial intelligence and web development.',
                'skills': ['React', 'Python', 'JavaScript', 'Node.js', 'MongoDB'],
                'interests': ['AI/ML', 'Web Development', 'Mobile Apps', 'Data Science'],
                'achievements': [
                    'Winner - University Hackathon 2024',
                    'Dean\'s List - Fall 2023',
                    'Best Project Award - Web Development',
                    'Completed 50+ Coding Challenges'
                ],
                'projects': [
                    {
                        'name': 'EchoVerse',
                        'description': 'AI-powered audiobook creation tool',
                        'tech': 'React, Python, IBM Watson'
                    },
                    {
                        'name': 'TaskMaster',
                        'description': 'Smart task management application',
                        'tech': 'React Native, Firebase'
                    },
                    {
                        'name': 'WeatherBot',
                        'description': 'Intelligent weather chatbot',
                        'tech': 'Python, NLP, API Integration'
                    }
                ]
            }
            
            user_id = db_manager.create_user(default_user_data)
            logger.info(f"Default user created with ID: {user_id}")
            
            # Add some sample audio history
            sample_histories = [
                {
                    'original_text': 'Once upon a time in a distant land, there lived a wise old wizard.',
                    'rewritten_text': '[CHEERFUL TONE] Once upon a time in a wonderfully distant land, there lived a delightfully wise old wizard!',
                    'tone': 'cheerful',
                    'voice': 'lisa',
                    'audio_generated': True
                },
                {
                    'original_text': 'The meeting will be held tomorrow at 3 PM.',
                    'rewritten_text': '[CONFIDENT TONE] The important meeting is scheduled for tomorrow at precisely 3 PM, and your attendance is expected.',
                    'tone': 'confident',
                    'voice': 'michael',
                    'audio_generated': False
                }
            ]
            
            for history in sample_histories:
                db_manager.create_audio_history(
                    user_id=user_id,
                    original_text=history['original_text'],
                    rewritten_text=history['rewritten_text'],
                    tone=history['tone'],
                    voice=history['voice'],
                    audio_generated=history['audio_generated']
                )
            
            logger.info("Sample audio history created")
        else:
            logger.info("Default user already exists")
        
        # Verify database setup
        tones = db_manager.get_tones()
        voices = db_manager.get_voices()
        
        logger.info(f"Database initialized successfully!")
        logger.info(f"Available tones: {len(tones)}")
        logger.info(f"Available voices: {len(voices)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = initialize_database()
    if success:
        print("✅ Database initialization completed successfully!")
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)
