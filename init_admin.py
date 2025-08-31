#!/usr/bin/env python3
"""
Initialize Admin User Script
Creates the admin user with the specified credentials.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_manager import DatabaseManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create the admin user"""
    try:
        db_manager = DatabaseManager()
        
        # Ensure database and tables exist
        db_manager.ensure_database_exists()
        
        # Admin credentials
        admin_name = "Srujan Reddy Nadipi"
        admin_email = "srujanreddynadipi@gmail.com"
        admin_password = "Srujan1980@"
        
        # Create admin user
        try:
            admin_id = db_manager.create_admin(admin_name, admin_email, admin_password)
            logger.info(f"✅ Admin user created successfully!")
            logger.info(f"   ID: {admin_id}")
            logger.info(f"   Name: {admin_name}")
            logger.info(f"   Email: {admin_email}")
            logger.info(f"   Password: {admin_password}")
            print("\n🎉 Admin user setup complete!")
            print(f"📧 Email: {admin_email}")
            print(f"🔑 Password: {admin_password}")
            
        except ValueError as e:
            if "already exists" in str(e):
                logger.info(f"ℹ️ Admin user already exists with email: {admin_email}")
                print(f"\n📧 Email: {admin_email}")
                print(f"🔑 Password: {admin_password}")
            else:
                raise
                
    except Exception as e:
        logger.error(f"❌ Error creating admin user: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Initializing EchoVerse Admin User...")
    create_admin_user()
