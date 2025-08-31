import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path='database/echoverse.db'):
        """Initialize database manager with SQLite database"""
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        try:
            # Create database directory if it doesn't exist
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create database and tables
            with sqlite3.connect(self.db_path) as conn:
                # Read and execute schema
                schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        conn.executescript(f.read())
                else:
                    logger.warning(f"Schema file not found at {schema_path}")
                    self._create_basic_tables(conn)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_basic_tables(self, conn):
        """Create basic tables if schema file is not found"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS audio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                rewritten_text TEXT NOT NULL,
                tone VARCHAR(50) NOT NULL,
                voice VARCHAR(50) NOT NULL,
                audio_generated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """Execute a query and return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    return dict(cursor.fetchone()) if cursor.fetchone() else None
                elif fetch_all:
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise
    
    # User management methods
    def create_user(self, user_data):
        """Create a new user"""
        query = """
            INSERT INTO users (name, email, phone, location, date_of_birth, 
                             university, course, year, roll_number, gpa, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user_data.get('name'),
            user_data.get('email'),
            user_data.get('phone'),
            user_data.get('location'),
            user_data.get('date_of_birth'),
            user_data.get('university'),
            user_data.get('course'),
            user_data.get('year'),
            user_data.get('roll_number'),
            user_data.get('gpa'),
            user_data.get('bio')
        )
        user_id = self.execute_query(query, params)
        
        # Add skills, interests, achievements, and projects
        if user_data.get('skills'):
            self.update_user_skills(user_id, user_data['skills'])
        if user_data.get('interests'):
            self.update_user_interests(user_id, user_data['interests'])
        if user_data.get('achievements'):
            self.update_user_achievements(user_id, user_data['achievements'])
        if user_data.get('projects'):
            self.update_user_projects(user_id, user_data['projects'])
        
        return user_id
    
    def get_user_by_email(self, email):
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            if user:
                user_dict = dict(user)
                user_dict['skills'] = self.get_user_skills(user_dict['id'])
                user_dict['interests'] = self.get_user_interests(user_dict['id'])
                user_dict['achievements'] = self.get_user_achievements(user_dict['id'])
                user_dict['projects'] = self.get_user_projects(user_dict['id'])
                return user_dict
            return None
    
    def update_user(self, user_id, user_data):
        """Update user information"""
        query = """
            UPDATE users SET name = ?, phone = ?, location = ?, date_of_birth = ?,
                           university = ?, course = ?, year = ?, roll_number = ?, 
                           gpa = ?, bio = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        params = (
            user_data.get('name'),
            user_data.get('phone'),
            user_data.get('location'),
            user_data.get('date_of_birth'),
            user_data.get('university'),
            user_data.get('course'),
            user_data.get('year'),
            user_data.get('roll_number'),
            user_data.get('gpa'),
            user_data.get('bio'),
            user_id
        )
        self.execute_query(query, params)
        
        # Update related data
        if 'skills' in user_data:
            self.update_user_skills(user_id, user_data['skills'])
        if 'interests' in user_data:
            self.update_user_interests(user_id, user_data['interests'])
        if 'achievements' in user_data:
            self.update_user_achievements(user_id, user_data['achievements'])
        if 'projects' in user_data:
            self.update_user_projects(user_id, user_data['projects'])
    
    def get_user_skills(self, user_id):
        """Get user skills"""
        query = "SELECT skill_name FROM user_skills WHERE user_id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def update_user_skills(self, user_id, skills):
        """Update user skills"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Delete existing skills
            cursor.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
            # Insert new skills
            for skill in skills:
                cursor.execute("INSERT INTO user_skills (user_id, skill_name) VALUES (?, ?)", 
                             (user_id, skill))
            conn.commit()
    
    def get_user_interests(self, user_id):
        """Get user interests"""
        query = "SELECT interest_name FROM user_interests WHERE user_id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def update_user_interests(self, user_id, interests):
        """Update user interests"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_interests WHERE user_id = ?", (user_id,))
            for interest in interests:
                cursor.execute("INSERT INTO user_interests (user_id, interest_name) VALUES (?, ?)", 
                             (user_id, interest))
            conn.commit()
    
    def get_user_achievements(self, user_id):
        """Get user achievements"""
        query = "SELECT achievement_text FROM user_achievements WHERE user_id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def update_user_achievements(self, user_id, achievements):
        """Update user achievements"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
            for achievement in achievements:
                cursor.execute("INSERT INTO user_achievements (user_id, achievement_text) VALUES (?, ?)", 
                             (user_id, achievement))
            conn.commit()
    
    def get_user_projects(self, user_id):
        """Get user projects"""
        query = "SELECT project_name, description, technologies FROM user_projects WHERE user_id = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            return [{'name': row[0], 'description': row[1], 'tech': row[2]} for row in cursor.fetchall()]
    
    def update_user_projects(self, user_id, projects):
        """Update user projects"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_projects WHERE user_id = ?", (user_id,))
            for project in projects:
                cursor.execute("""INSERT INTO user_projects (user_id, project_name, description, technologies) 
                                VALUES (?, ?, ?, ?)""", 
                             (user_id, project.get('name'), project.get('description'), project.get('tech')))
            conn.commit()
    
    # Audio history methods
    def create_audio_history(self, user_id, original_text, rewritten_text, tone, voice, audio_generated=False):
        """Create audio history entry"""
        query = """
            INSERT INTO audio_history (user_id, original_text, rewritten_text, tone, voice, audio_generated)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (user_id, original_text, rewritten_text, tone, voice, audio_generated)
        return self.execute_query(query, params)
    
    def get_user_audio_history(self, user_id, limit=50):
        """Get user's audio history"""
        query = """
            SELECT * FROM audio_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_audio_generated(self, history_id, audio_file_path=None):
        """Update audio generation status"""
        query = """
            UPDATE audio_history 
            SET audio_generated = TRUE, audio_file_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        self.execute_query(query, (audio_file_path, history_id))
    
    def delete_audio_history(self, history_id, user_id):
        """Delete audio history entry"""
        query = "DELETE FROM audio_history WHERE id = ? AND user_id = ?"
        self.execute_query(query, (history_id, user_id))
    
    def get_tones(self):
        """Get all available tones"""
        query = "SELECT * FROM tones WHERE is_active = TRUE"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_voices(self):
        """Get all available voices"""
        query = "SELECT * FROM voices WHERE is_active = TRUE"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

# Initialize database manager
db_manager = DatabaseManager()
