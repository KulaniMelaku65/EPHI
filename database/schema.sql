-- EPHI Training Management System Database Schema
-- SQLite Database

-- Users table with role-based access
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'trainer', 'trainee', 'external')),
    phone TEXT,
    position TEXT,
    health_facility_id INTEGER,
    region TEXT,
    years_experience INTEGER,
    education_level TEXT,
    profile_image TEXT,
    is_active BOOLEAN DEFAULT 1,
    is_verified BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (health_facility_id) REFERENCES health_facilities(id)
);

-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Health facilities table
CREATE TABLE IF NOT EXISTS health_facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    woreda TEXT,
    facility_type TEXT CHECK(facility_type IN ('Hospital', 'Health Center', 'Clinic', 'Laboratory', 'Regional Bureau')),
    address TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Training topics table
CREATE TABLE IF NOT EXISTS training_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    duration_days INTEGER NOT NULL,
    category TEXT CHECK(category IN ('Disease Surveillance', 'Laboratory', 'Emergency Response', 'Data Management', 'Immunization', 'Other')),
    prerequisites TEXT,
    learning_objectives TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Training sessions table
CREATE TABLE IF NOT EXISTS training_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    trainer_id INTEGER NOT NULL,
    health_facility_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    max_participants INTEGER DEFAULT 50,
    status TEXT DEFAULT 'scheduled' CHECK(status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    location_details TEXT,
    materials TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES training_topics(id),
    FOREIGN KEY (trainer_id) REFERENCES users(id),
    FOREIGN KEY (health_facility_id) REFERENCES health_facilities(id)
);

-- Training registrations table
CREATE TABLE IF NOT EXISTS training_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    trainee_id INTEGER NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    attendance_status TEXT DEFAULT 'registered' CHECK(attendance_status IN ('registered', 'attended', 'absent', 'cancelled')),
    pre_test_score REAL,
    post_test_score REAL,
    completion_status TEXT DEFAULT 'enrolled' CHECK(completion_status IN ('enrolled', 'in_progress', 'completed', 'failed', 'withdrawn')),
    certificate_issued BOOLEAN DEFAULT 0,
    certificate_number TEXT,
    feedback_rating INTEGER CHECK(feedback_rating BETWEEN 1 AND 5),
    feedback_comments TEXT,
    UNIQUE(session_id, trainee_id),
    FOREIGN KEY (session_id) REFERENCES training_sessions(id),
    FOREIGN KEY (trainee_id) REFERENCES users(id)
);

-- Funding requests table
CREATE TABLE IF NOT EXISTS funding_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    requested_amount REAL NOT NULL,
    currency TEXT DEFAULT 'ETB',
    num_participants INTEGER,
    duration_days INTEGER,
    justification TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'funded')),
    approved_by INTEGER,
    approved_amount REAL,
    approval_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trainer_id) REFERENCES users(id),
    FOREIGN KEY (topic_id) REFERENCES training_topics(id),
    FOREIGN KEY (approved_by) REFERENCES users(id)
);

-- Certificates table
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL,
    certificate_number TEXT UNIQUE NOT NULL,
    issue_date DATE NOT NULL,
    pdf_path TEXT,
    qr_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (registration_id) REFERENCES training_registrations(id)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('training_reminder', 'registration_confirmed', 'certificate_ready', 'funding_update', 'system_announcement')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Email logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT,
    status TEXT CHECK(status IN ('sent', 'failed', 'pending')),
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics table for tracking system usage
CREATE TABLE IF NOT EXISTS analytics_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action_type TEXT,
    resource_type TEXT,
    resource_id INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Password reset / email verification tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    token_type TEXT DEFAULT 'reset' CHECK(token_type IN ('reset', 'verify')),
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Trainee registration forms (created by trainers)
CREATE TABLE IF NOT EXISTS registration_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    form_name TEXT NOT NULL,
    form_status TEXT DEFAULT 'active' CHECK(form_status IN ('draft', 'active', 'closed')),
    form_description TEXT,
    share_link TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trainer_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES training_sessions(id)
);

-- Trainee form submissions
CREATE TABLE IF NOT EXISTS registration_form_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    health_facility TEXT NOT NULL,
    region TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approval_status TEXT DEFAULT 'pending' CHECK(approval_status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by INTEGER,
    FOREIGN KEY (form_id) REFERENCES registration_forms(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_sessions_trainer ON training_sessions(trainer_id);
CREATE INDEX idx_sessions_dates ON training_sessions(start_date, end_date);
CREATE INDEX idx_registrations_session ON training_registrations(session_id);
CREATE INDEX idx_registrations_trainee ON training_registrations(trainee_id);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);

-- Sample data for demonstration
INSERT INTO regions (name, code, description) VALUES
('Addis Ababa', 'AA', 'Capital city region'),
('Oromia', 'OR', 'Oromia regional state'),
('Amhara', 'AM', 'Amhara regional state'),
('Somali', 'SO', 'Somali regional state'),
('Tigray', 'TI', 'Tigray regional state'),
('SNNPR', 'SN', 'Southern Nations, Nationalities and Peoples Region'),
('Dire Dawa', 'DD', 'Dire Dawa city administration'),
('Afar', 'AF', 'Afar regional state'),
('Benishangul-Gumuz', 'BG', 'Benishangul-Gumuz regional state'),
('Gambela', 'GA', 'Gambela regional state'),
('Harari', 'HA', 'Harari regional state');

INSERT INTO health_facilities (name, region, facility_type) VALUES
('Jimma University Medical Center', 'Oromia', 'Hospital'),
('Gondar Hospital', 'Amhara', 'Hospital'),
('Harar Health Bureau', 'Somali', 'Regional Bureau'),
('Mekelle Hospital', 'Tigray', 'Hospital'),
('Hawassa Hospital', 'SNNPR', 'Hospital'),
('Addis Ababa Central Hospital', 'Addis Ababa', 'Hospital'),
('Bahir Dar Hospital', 'Amhara', 'Hospital'),
('Dire Dawa Health Bureau', 'Dire Dawa', 'Regional Bureau'),
('Adama Hospital', 'Oromia', 'Hospital'),
('Dessie Hospital', 'Amhara', 'Hospital');

-- Sample users (passwords are hashed in production)
INSERT INTO users (email, password_hash, full_name, role, phone, position, health_facility_id, region) VALUES
('admin@ephi.gov.et', '$2b$12$abcdefghijklmnopqrstuvwxyz', 'Dr. Alemayehu Bekele', 'admin', '+251911234567', 'Director General', 6, 'Addis Ababa'),
('trainer@ephi.gov.et', '$2b$12$abcdefghijklmnopqrstuvwxyz', 'Dr. Abebe Tadesse', 'trainer', '+251911234568', 'Senior Trainer', 1, 'Oromia'),
('trainee@ephi.gov.et', '$2b$12$abcdefghijklmnopqrstuvwxyz', 'Tigist Mengistu', 'trainee', '+251911234569', 'Laboratory Technician', 2, 'Amhara'),
('external@who.int', '$2b$12$abcdefghijklmnopqrstuvwxyz', 'WHO Observer', 'external', NULL, 'Program Officer', NULL, NULL);

INSERT INTO training_topics (title, description, duration_days, category) VALUES
('Disease Surveillance and Reporting', 'Comprehensive training on IDSR system and disease reporting mechanisms', 5, 'Disease Surveillance'),
('Laboratory Quality Assurance', 'Quality management systems for diagnostic laboratories', 4, 'Laboratory'),
('Emergency Outbreak Response', 'Rapid response protocols for disease outbreaks', 5, 'Emergency Response'),
('Data Management Systems', 'DHIS2 and health information management', 3, 'Data Management'),
('Immunization Program Management', 'EPI program planning and implementation', 5, 'Immunization'),
('Cholera Response Protocol', 'Cholera outbreak detection and response', 3, 'Emergency Response'),
('Laboratory Diagnostics', 'Advanced diagnostic techniques', 5, 'Laboratory'),
('Malaria Case Management', 'Diagnosis and treatment of malaria', 4, 'Disease Surveillance');

INSERT INTO training_sessions (topic_id, trainer_id, health_facility_id, start_date, end_date, status) VALUES
(1, 2, 1, '2026-05-15', '2026-05-19', 'completed'),
(2, 2, 2, '2026-05-20', '2026-05-24', 'in_progress'),
(3, 2, 3, '2026-05-25', '2026-05-29', 'scheduled');

-- Sample registrations: trainee (id=3) enrolled in sessions 1 & 2
INSERT INTO training_registrations (session_id, trainee_id, completion_status, certificate_issued, certificate_number) VALUES
(1, 3, 'completed', 1, 'EPHI-2026-DS-1247'),
(2, 3, 'enrolled', 0, NULL);

-- Certificate for the completed registration (registration id=1)
INSERT INTO certificates (registration_id, certificate_number, issue_date) VALUES
(1, 'EPHI-2026-DS-1247', '2026-05-19');
