-- MySQL version of the EchoVerse database schema
-- Use this for MySQL/MariaDB database

-- Users/Students table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    location VARCHAR(100),
    date_of_birth DATE,
    university VARCHAR(200),
    course VARCHAR(200),
    year VARCHAR(20),
    roll_number VARCHAR(50),
    gpa DECIMAL(3,2),
    bio TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- User Skills table
CREATE TABLE IF NOT EXISTS user_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Interests table
CREATE TABLE IF NOT EXISTS user_interests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    interest_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Achievements table
CREATE TABLE IF NOT EXISTS user_achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    achievement_text TEXT NOT NULL,
    achievement_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User Projects table
CREATE TABLE IF NOT EXISTS user_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    project_name VARCHAR(200) NOT NULL,
    description TEXT,
    technologies TEXT,
    project_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Audio History table
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
);

-- Tones configuration table
CREATE TABLE IF NOT EXISTS tones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tone_id VARCHAR(50) UNIQUE NOT NULL,
    tone_name VARCHAR(100) NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Voices configuration table
CREATE TABLE IF NOT EXISTS voices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voice_id VARCHAR(50) UNIQUE NOT NULL,
    voice_name VARCHAR(100) NOT NULL,
    description TEXT,
    watson_voice_id VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Downloads table
CREATE TABLE IF NOT EXISTS downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    history_id INT,
    filename VARCHAR(255) NOT NULL,
    original_text TEXT,
    rewritten_text TEXT,
    tone VARCHAR(50),
    voice VARCHAR(50),
    file_size BIGINT,
    source VARCHAR(20) DEFAULT 'generator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (history_id) REFERENCES audio_history(id) ON DELETE SET NULL
);

-- Admin table
CREATE TABLE IF NOT EXISTS admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default tones
INSERT IGNORE INTO tones (tone_id, tone_name, description, prompt_template) VALUES
('neutral', 'Neutral', 'Clear and balanced narration', 'Rewrite the following text in a clear, balanced, and professional tone while maintaining the original meaning:'),
('suspenseful', 'Suspenseful', 'Dramatic and engaging delivery', 'Rewrite the following text to create suspense and drama, making it more engaging and thrilling while preserving the core message:'),
('inspiring', 'Inspiring', 'Uplifting and motivational tone', 'Rewrite the following text in an uplifting, motivational, and inspiring tone that encourages and energizes the reader:'),
('cheerful', 'Cheerful', 'Bright, happy, and energetic', 'Rewrite the following text in a bright, happy, and energetic tone that conveys joy and positivity:'),
('sad', 'Sad', 'Soft, somber, and emotional', 'Rewrite the following text in a soft, somber, and emotional tone that conveys melancholy and reflection:'),
('angry', 'Angry', 'Intense and passionate delivery', 'Rewrite the following text with intensity and passion, conveying strong emotions and determination:'),
('playful', 'Playful', 'Fun, lively, and whimsical', 'Rewrite the following text in a fun, lively, and whimsical tone that is entertaining and lighthearted:'),
('calm', 'Calm', 'Relaxed and soothing narration', 'Rewrite the following text in a relaxed, soothing, and peaceful tone that promotes tranquility:'),
('confident', 'Confident', 'Assured and persuasive', 'Rewrite the following text in an assured, persuasive, and authoritative tone that conveys certainty and leadership:');

-- Insert default voices
INSERT IGNORE INTO voices (voice_id, voice_name, description, watson_voice_id) VALUES
('lisa', 'Lisa', 'Warm and professional female voice', 'en-US_LisaV3Voice'),
('michael', 'Michael', 'Confident and clear male voice', 'en-US_MichaelV3Voice'),
('allison', 'Allison', 'Friendly and expressive female voice', 'en-US_AllisonV3Voice');

-- Create indexes for better performance (only create if tables exist and indexes don't exist)
-- These will be created by the application as needed
