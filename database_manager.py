import pymysql
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Initialize database manager with MySQL database"""
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USERNAME'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_DATABASE'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
    
    def get_connection(self):
        """Get database connection"""
        return pymysql.connect(**self.db_config)
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        try:
            # First connect without specifying database to create it if needed
            config_without_db = self.db_config.copy()
            database_name = config_without_db.pop('database')
            
            with pymysql.connect(**config_without_db) as conn:
                with conn.cursor() as cursor:
                    # Create database if it doesn't exist
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
                    conn.commit()
            
            # Now connect to the specific database and create tables
            with self.get_connection() as conn:
                # Read and execute schema
                schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema_mysql.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        # Split the SQL file into individual statements
                        statements = f.read().split(';')
                        with conn.cursor() as cursor:
                            for statement in statements:
                                statement = statement.strip()
                                if statement:
                                    cursor.execute(statement)
                            conn.commit()
                else:
                    logger.warning(f"Schema file not found at {schema_path}")
                    self._create_basic_tables(conn)
                
        except Exception as e:
            logger.error(f"Error ensuring database exists: {e}")
            raise
    
    def _create_basic_tables(self, conn):
        """Create basic tables if schema file is not found"""
        with conn.cursor() as cursor:
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(20),
                    location VARCHAR(100),
                    date_of_birth DATE,
                    university VARCHAR(200),
                    course VARCHAR(200),
                    year VARCHAR(20),
                    roll_number VARCHAR(50),
                    gpa DECIMAL(3,2),
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')
            
            # Audio history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    original_text TEXT NOT NULL,
                    rewritten_text TEXT NOT NULL,
                    tone VARCHAR(50) NOT NULL,
                    voice VARCHAR(50) NOT NULL,
                    audio_file_path VARCHAR(500),
                    audio_generated BOOLEAN DEFAULT FALSE,
                    processing_status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Downloads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS downloads (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    history_id INT NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    stored_filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size BIGINT,
                    mime_type VARCHAR(100),
                    download_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_downloaded_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (history_id) REFERENCES audio_history(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()

    # User Management Methods
    def create_user(self, name, email, **kwargs):
        """Create a new user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build dynamic insert statement
                    fields = ['name', 'email'] + list(kwargs.keys())
                    values = [name, email] + list(kwargs.values())
                    placeholders = ', '.join(['%s'] * len(values))
                    field_names = ', '.join(fields)
                    
                    query = f'''
                        INSERT INTO users ({field_names})
                        VALUES ({placeholders})
                    '''
                    
                    cursor.execute(query, values)
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    def get_user(self, user_id):
        """Get user by ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def update_user(self, user_id, **kwargs):
        """Update user information"""
        if not kwargs:
            return False
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build dynamic update statement
                    set_clauses = []
                    values = []
                    
                    for field, value in kwargs.items():
                        set_clauses.append(f"{field} = %s")
                        values.append(value)
                    
                    values.append(user_id)
                    
                    query = f'''
                        UPDATE users 
                        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    '''
                    
                    cursor.execute(query, values)
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id):
        """Delete user and all related data"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    # Authentication Methods
    def hash_password(self, password):
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password, hashed_password):
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def register_user(self, name, email, password, **kwargs):
        """Register a new user with password"""
        try:
            # Check if user already exists
            existing_user = self.get_user_by_email(email)
            if existing_user:
                return None, "User with this email already exists"

            # Hash the password
            password_hash = self.hash_password(password)

            # Create user with hashed password
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build dynamic insert statement
                    fields = ['name', 'email', 'password_hash'] + list(kwargs.keys())
                    values = [name, email, password_hash] + list(kwargs.values())
                    placeholders = ', '.join(['%s'] * len(values))
                    field_names = ', '.join(fields)
                    
                    query = f'''
                        INSERT INTO users ({field_names})
                        VALUES ({placeholders})
                    '''
                    
                    cursor.execute(query, values)
                    conn.commit()
                    user_id = cursor.lastrowid
                    
                    # Return the created user (without password)
                    return self.get_user(user_id), "User registered successfully"
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return None, f"Registration failed: {str(e)}"

    def authenticate_user(self, email, password):
        """Authenticate a user with email and password"""
        try:
            user = self.get_user_by_email(email)
            if not user:
                return None, "Invalid email or password"

            if not self.verify_password(password, user['password_hash']):
                return None, "Invalid email or password"

            # Update last login
            self.update_user(user['id'], last_login=datetime.now())

            # Remove password hash from returned user data
            user_data = dict(user)
            del user_data['password_hash']
            
            return user_data, "Login successful"
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None, "Authentication failed"

    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE users 
                        SET last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (user_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    # User Skills Methods
    def add_user_skill(self, user_id, skill_name):
        """Add a skill to user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO user_skills (user_id, skill_name)
                        VALUES (%s, %s)
                    ''', (user_id, skill_name))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding user skill: {e}")
            return None

    def get_user_skills(self, user_id):
        """Get all skills for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM user_skills 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC
                    ''', (user_id,))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user skills: {e}")
            return []

    def remove_user_skill(self, user_id, skill_id):
        """Remove a skill from user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM user_skills 
                        WHERE id = %s AND user_id = %s
                    ''', (skill_id, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user skill: {e}")
            return False

    # User Interests Methods
    def add_user_interest(self, user_id, interest_name):
        """Add an interest to user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO user_interests (user_id, interest_name)
                        VALUES (%s, %s)
                    ''', (user_id, interest_name))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding user interest: {e}")
            return None

    def get_user_interests(self, user_id):
        """Get all interests for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM user_interests 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC
                    ''', (user_id,))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user interests: {e}")
            return []

    def remove_user_interest(self, user_id, interest_id):
        """Remove an interest from user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM user_interests 
                        WHERE id = %s AND user_id = %s
                    ''', (interest_id, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user interest: {e}")
            return False

    # User Achievements Methods
    def add_user_achievement(self, user_id, achievement_text, achievement_date=None):
        """Add an achievement to user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO user_achievements (user_id, achievement_text, achievement_date)
                        VALUES (%s, %s, %s)
                    ''', (user_id, achievement_text, achievement_date))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding user achievement: {e}")
            return None

    def get_user_achievements(self, user_id):
        """Get all achievements for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM user_achievements 
                        WHERE user_id = %s 
                        ORDER BY achievement_date DESC, created_at DESC
                    ''', (user_id,))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []

    def remove_user_achievement(self, user_id, achievement_id):
        """Remove an achievement from user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM user_achievements 
                        WHERE id = %s AND user_id = %s
                    ''', (achievement_id, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user achievement: {e}")
            return False

    # User Projects Methods
    def add_user_project(self, user_id, project_name, description=None, technologies=None, project_url=None):
        """Add a project to user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO user_projects (user_id, project_name, description, technologies, project_url)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (user_id, project_name, description, technologies, project_url))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding user project: {e}")
            return None

    def get_user_projects(self, user_id):
        """Get all projects for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM user_projects 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC
                    ''', (user_id,))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user projects: {e}")
            return []

    def remove_user_project(self, user_id, project_id):
        """Remove a project from user profile"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM user_projects 
                        WHERE id = %s AND user_id = %s
                    ''', (project_id, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing user project: {e}")
            return False

    # Audio History Methods
    def save_audio_history(self, user_id, original_text, rewritten_text, tone, voice, audio_file_path=None):
        """Save audio generation history"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO audio_history 
                        (user_id, original_text, rewritten_text, tone, voice, audio_file_path, audio_generated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (user_id, original_text, rewritten_text, tone, voice, audio_file_path, audio_file_path is not None))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving audio history: {e}")
            return None

    def get_user_audio_history(self, user_id, limit=50):
        """Get audio history for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM audio_history 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    ''', (user_id, limit))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting audio history: {e}")
            return []

    def get_audio_history_by_id(self, history_id):
        """Get a specific audio history item by ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM audio_history 
                        WHERE id = %s
                    ''', (history_id,))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting audio history by ID: {e}")
            return None

    def update_audio_history_status(self, history_id, status, audio_file_path=None):
        """Update audio history processing status"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if audio_file_path:
                        cursor.execute('''
                            UPDATE audio_history 
                            SET processing_status = %s, audio_file_path = %s, audio_generated = TRUE, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (status, audio_file_path, history_id))
                    else:
                        cursor.execute('''
                            UPDATE audio_history 
                            SET processing_status = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (status, history_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating audio history status: {e}")
            return False

    def delete_audio_history(self, user_id, history_id):
        """Delete a specific audio history entry"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM audio_history 
                        WHERE id = %s AND user_id = %s
                    ''', (history_id, user_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting audio history: {e}")
            return False

    # Configuration Methods
    def get_available_tones(self):
        """Get all available tones"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM tones WHERE is_active = TRUE ORDER BY tone_name')
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting tones: {e}")
            return []

    def get_available_voices(self):
        """Get all available voices"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM voices WHERE is_active = TRUE ORDER BY voice_name')
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting voices: {e}")
            return []

    def get_tone_prompt(self, tone_id):
        """Get prompt template for a specific tone"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT prompt_template FROM tones WHERE tone_id = %s AND is_active = TRUE', (tone_id,))
                    result = cursor.fetchone()
                    return result['prompt_template'] if result else None
        except Exception as e:
            logger.error(f"Error getting tone prompt: {e}")
            return None

    def get_voice_watson_id(self, voice_id):
        """Get Watson voice ID for a specific voice"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT watson_voice_id FROM voices WHERE voice_id = %s AND is_active = TRUE', (voice_id,))
                    result = cursor.fetchone()
                    return result['watson_voice_id'] if result else None
        except Exception as e:
            logger.error(f"Error getting Watson voice ID: {e}")
            return None

    # Utility Methods
    def get_database_stats(self):
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    stats = {}
                    
                    # Count users
                    cursor.execute('SELECT COUNT(*) as count FROM users')
                    stats['users'] = cursor.fetchone()['count']
                    
                    # Count audio history
                    cursor.execute('SELECT COUNT(*) as count FROM audio_history')
                    stats['audio_history'] = cursor.fetchone()['count']
                    
                    # Count downloads
                    cursor.execute('SELECT COUNT(*) as count FROM downloads')
                    stats['downloads'] = cursor.fetchone()['count']
                    
                    # Count tones
                    cursor.execute('SELECT COUNT(*) as count FROM tones WHERE is_active = TRUE')
                    stats['active_tones'] = cursor.fetchone()['count']
                    
                    # Count voices
                    cursor.execute('SELECT COUNT(*) as count FROM voices WHERE is_active = TRUE')
                    stats['active_voices'] = cursor.fetchone()['count']
                    
                    return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    # Download Management Methods
    def save_download(self, user_id, history_id, original_filename, stored_filename, file_path, file_size=None, mime_type=None):
        """Save download record"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO downloads 
                        (user_id, history_id, original_filename, stored_filename, file_path, file_size, mime_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (user_id, history_id, original_filename, stored_filename, file_path, file_size, mime_type))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving download: {e}")
            return None

    def get_user_downloads(self, user_id, limit=50):
        """Get downloads for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT d.*, ah.original_text, ah.rewritten_text, ah.tone, ah.voice 
                        FROM downloads d
                        JOIN audio_history ah ON d.history_id = ah.id
                        WHERE d.user_id = %s 
                        ORDER BY d.created_at DESC 
                        LIMIT %s
                    ''', (user_id, limit))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting user downloads: {e}")
            return []

    def get_download_by_id(self, download_id, user_id=None):
        """Get download by ID, optionally filtered by user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if user_id:
                        cursor.execute('''
                            SELECT d.*, ah.original_text, ah.rewritten_text, ah.tone, ah.voice 
                            FROM downloads d
                            JOIN audio_history ah ON d.history_id = ah.id
                            WHERE d.id = %s AND d.user_id = %s
                        ''', (download_id, user_id))
                    else:
                        cursor.execute('''
                            SELECT d.*, ah.original_text, ah.rewritten_text, ah.tone, ah.voice 
                            FROM downloads d
                            JOIN audio_history ah ON d.history_id = ah.id
                            WHERE d.id = %s
                        ''', (download_id,))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting download by ID: {e}")
            return None

    def update_download_stats(self, download_id):
        """Update download statistics (count and last downloaded time)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE downloads 
                        SET download_count = download_count + 1, 
                            last_downloaded_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (download_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating download stats: {e}")
            return False

    def delete_download(self, download_id, user_id=None):
        """Delete download record and associated file"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get download info first
                    if user_id:
                        cursor.execute('SELECT * FROM downloads WHERE id = %s AND user_id = %s', (download_id, user_id))
                    else:
                        cursor.execute('SELECT * FROM downloads WHERE id = %s', (download_id,))
                    
                    download = cursor.fetchone()
                    if not download:
                        return False
                    
                    # Delete from database
                    cursor.execute('DELETE FROM downloads WHERE id = %s', (download_id,))
                    conn.commit()
                    
                    # Try to delete physical file
                    try:
                        if os.path.exists(download['file_path']):
                            os.remove(download['file_path'])
                    except Exception as e:
                        logger.warning(f"Could not delete file {download['file_path']}: {e}")
                    
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting download: {e}")
            return False

    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    # Alias methods for backward compatibility with app.py
    def get_tones(self):
        """Alias for get_available_tones"""
        return self.get_available_tones()

    def get_voices(self):
        """Alias for get_available_voices"""
        return self.get_available_voices()

    # Admin Management Methods
    def create_admin(self, name, email, password):
        """Create a new admin user"""
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO admins (name, email, password_hash)
                        VALUES (%s, %s, %s)
                    ''', (name, email, password_hash))
                    conn.commit()
                    admin_id = cursor.lastrowid
                    
                    logger.info(f"Admin created successfully with ID: {admin_id}")
                    return admin_id
                    
        except pymysql.err.IntegrityError as e:
            if 'Duplicate entry' in str(e):
                logger.error(f"Admin with email {email} already exists")
                raise ValueError("Admin with this email already exists")
            else:
                logger.error(f"Database integrity error creating admin: {e}")
                raise
        except Exception as e:
            logger.error(f"Error creating admin: {e}")
            raise

    def authenticate_admin(self, email, password):
        """Authenticate admin login"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, email, password_hash, role, is_active
                        FROM admins 
                        WHERE email = %s AND is_active = TRUE
                    ''', (email,))
                    
                    admin = cursor.fetchone()
                    
                    if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                        # Update last login
                        cursor.execute('''
                            UPDATE admins SET last_login = NOW() WHERE id = %s
                        ''', (admin['id'],))
                        conn.commit()
                        
                        # Remove password hash from returned data
                        admin.pop('password_hash')
                        logger.info(f"Admin authenticated successfully: {email}")
                        return admin
                    else:
                        logger.warning(f"Failed admin authentication attempt: {email}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error authenticating admin: {e}")
            raise

    def get_admin_metrics(self):
        """Get admin dashboard metrics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get user count
                    cursor.execute('SELECT COUNT(*) as count FROM users')
                    users_count = cursor.fetchone()['count']
                    
                    # Get new signups today
                    cursor.execute('''
                        SELECT COUNT(*) as count FROM users 
                        WHERE DATE(created_at) = CURDATE()
                    ''')
                    new_signups_today = cursor.fetchone()['count']
                    
                    # Get content uploaded (audio history count)
                    cursor.execute('SELECT COUNT(*) as count FROM audio_history')
                    content_uploaded = cursor.fetchone()['count']
                    
                    # Get flagged items (for now, return 0 as we don't have flagging system)
                    flagged_items = 0
                    
                    return {
                        'usersCount': users_count,
                        'newSignupsToday': new_signups_today,
                        'contentUploaded': content_uploaded,
                        'flaggedItems': flagged_items
                    }
                    
        except Exception as e:
            logger.error(f"Error getting admin metrics: {e}")
            raise

    def get_recent_users(self, limit=10):
        """Get recent users for admin dashboard"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, email, created_at, 
                               CASE WHEN is_verified THEN 'Active' ELSE 'Pending' END as status
                        FROM users 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    ''', (limit,))
                    
                    users = cursor.fetchall()
                    return users
                    
        except Exception as e:
            logger.error(f"Error getting recent users: {e}")
            raise

    def get_system_health(self):
        """Get system health metrics"""
        try:
            # Mock data for now - in production you'd get real metrics
            return {
                'storagePercent': 45,
                'uptimeSeconds': 86400  # 1 day
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            raise

    def save_study_material(self, user_id, title, content, chapters, file_type):
        """Save study material to database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create study_materials table if it doesn't exist
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS study_materials (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            title VARCHAR(255) NOT NULL,
                            content LONGTEXT NOT NULL,
                            chapters JSON NOT NULL,
                            file_type VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """)
                    
                    # Insert study material
                    cursor.execute("""
                        INSERT INTO study_materials (user_id, title, content, chapters, file_type)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, title, content, chapters, file_type))
                    
                    material_id = cursor.lastrowid
                    conn.commit()
                    
                    logger.info(f"Study material saved with ID: {material_id}")
                    return material_id
                    
        except Exception as e:
            logger.error(f"Error saving study material: {e}")
            raise

    def get_user_study_materials(self, user_id):
        """Get all study materials for a user"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, title, file_type, created_at, updated_at
                        FROM study_materials
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                    """, (user_id,))
                    
                    return cursor.fetchall()
                    
        except Exception as e:
            logger.error(f"Error getting user study materials: {e}")
            raise

    def get_study_material(self, material_id, user_id):
        """Get specific study material"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM study_materials
                        WHERE id = %s AND user_id = %s
                    """, (material_id, user_id))
                    
                    return cursor.fetchone()
                    
        except Exception as e:
            logger.error(f"Error getting study material: {e}")
            raise

    def delete_study_material(self, material_id, user_id):
        """Delete study material"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM study_materials
                        WHERE id = %s AND user_id = %s
                    """, (material_id, user_id))
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
        except Exception as e:
            logger.error(f"Error deleting study material: {e}")
            raise
