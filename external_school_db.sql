-- External School Database Setup
-- Basic database, table creation, and sample data load

-- Create the database if it doesn’t exist
CREATE DATABASE IF NOT EXISTS external_school_db;

-- Select the database
USE external_school_db;

-- Drop table if it exists (safety, optional)
DROP TABLE IF EXISTS fyp_data;

-- Create the main table
CREATE TABLE fyp_data (
    id_num INT AUTO_INCREMENT PRIMARY KEY,
    id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    course VARCHAR(200) NOT NULL,
    fyp_session VARCHAR(100) NOT NULL,
    fyp_eligible BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active',
    role VARCHAR(50) DEFAULT 'student',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data (5 roles)
INSERT INTO fyp_data (id, name, email, course, fyp_session, role) VALUES
('AC001', 'Tan Zhang Hong', 'tanzhanghong2009@gmail.com', 'Information Systems', '2025-Sem1', 'academic coordinator'),
('ST001', 'Project', 'projectflow25@gmail.com', 'Computer Science', '2025-Sem1', 'student'),
('SV001', 'Jeff', 'zhtan034@mymail.sim.edu.sg', 'Software Engineering', '2025-Sem1', 'supervisor'),
('AS001', 'Daniel Ho', 'daniel.ho@example.com', 'Data Science', '2025-Sem1', 'assessor');
