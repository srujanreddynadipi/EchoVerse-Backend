#!/usr/bin/env python3
"""
Database migration script to add authentication fields to existing users table
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Add authentication fields to existing users table"""
    try:
        # Database configuration
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_DATABASE'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        print("🔄 Starting database migration...")
        
        with pymysql.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                # Check if password_hash column exists
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'password_hash'
                """, (db_config['database'],))
                
                result = cursor.fetchone()
                
                if result['count'] == 0:
                    print("➕ Adding password_hash column...")
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''
                    """)
                else:
                    print("✅ password_hash column already exists")
                
                # Check if is_verified column exists
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'is_verified'
                """, (db_config['database'],))
                
                result = cursor.fetchone()
                
                if result['count'] == 0:
                    print("➕ Adding is_verified column...")
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN is_verified BOOLEAN DEFAULT FALSE
                    """)
                else:
                    print("✅ is_verified column already exists")
                
                # Check if last_login column exists
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'last_login'
                """, (db_config['database'],))
                
                result = cursor.fetchone()
                
                if result['count'] == 0:
                    print("➕ Adding last_login column...")
                    cursor.execute("""
                        ALTER TABLE users 
                        ADD COLUMN last_login TIMESTAMP NULL
                    """)
                else:
                    print("✅ last_login column already exists")
                
                conn.commit()
                print("✅ Database migration completed successfully!")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 EchoVerse Database Migration")
    print("=" * 40)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed! Your database is ready for authentication.")
    else:
        print("\n💥 Migration failed. Please check your database configuration.")
