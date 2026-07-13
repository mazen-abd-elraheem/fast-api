-- =============================================
-- Sanaie Platform — MySQL Database Schema v2.0
-- Run in MySQL Workbench against `sanaie_db`
-- =============================================

CREATE DATABASE IF NOT EXISTS sanaie_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sanaie_db;

-- =============================================
-- USERS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('client', 'worker', 'admin') NOT NULL DEFAULT 'client',
    latitude DOUBLE NULL,
    longitude DOUBLE NULL,
    skills JSON NULL,
    profile_image_url VARCHAR(500) NULL,
    is_available VARCHAR(20) NOT NULL DEFAULT 'available',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id),
    UNIQUE INDEX ix_users_email (email),
    INDEX ix_users_role (role),
    INDEX ix_users_location (latitude, longitude)
) ENGINE=InnoDB;

-- =============================================
-- JOBS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS jobs (
    job_id VARCHAR(36) NOT NULL,
    client_id VARCHAR(36) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category ENUM('plumbing', 'electrical', 'painting', 'carpentry', 'cleaning', 'general', 'other') NOT NULL,
    status ENUM('open', 'in_progress', 'on_the_way', 'work_started', 'completed', 'canceled') NOT NULL DEFAULT 'open',
    image_url VARCHAR(500) NULL,
    initial_price DECIMAL(10, 2) NOT NULL,
    latitude DOUBLE NULL,
    longitude DOUBLE NULL,
    address VARCHAR(500) NULL,
    assigned_worker_id VARCHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (job_id),
    INDEX ix_jobs_status (status),
    INDEX ix_jobs_category (category),
    INDEX ix_jobs_client_id (client_id),
    INDEX ix_jobs_created_at (created_at DESC),
    FULLTEXT INDEX ft_jobs_search (title, description),

    CONSTRAINT fk_jobs_client FOREIGN KEY (client_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_jobs_worker FOREIGN KEY (assigned_worker_id)
        REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================
-- BIDS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS bids (
    bid_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(36) NOT NULL,
    worker_id VARCHAR(36) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    message TEXT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'withdrawn') NOT NULL DEFAULT 'pending',
    scheduled_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (bid_id),
    INDEX ix_bids_job_id (job_id),
    INDEX ix_bids_worker_id (worker_id),

    -- Enforce one bid per worker per job
    UNIQUE INDEX uq_one_bid_per_worker_per_job (job_id, worker_id),

    CONSTRAINT fk_bids_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_bids_worker FOREIGN KEY (worker_id)
        REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================
-- REVIEWS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS reviews (
    review_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(36) NOT NULL,
    client_id VARCHAR(36) NOT NULL,
    worker_id VARCHAR(36) NOT NULL,
    rating_score INT NOT NULL,
    comment TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (review_id),
    -- One review per job
    UNIQUE INDEX uq_one_review_per_job (job_id),
    INDEX ix_reviews_worker_id (worker_id),
    INDEX ix_reviews_client_id (client_id),

    -- Rating must be 1–5
    CONSTRAINT ck_rating_range CHECK (rating_score >= 1 AND rating_score <= 5),

    CONSTRAINT fk_reviews_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_client FOREIGN KEY (client_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_worker FOREIGN KEY (worker_id)
        REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================
-- NOTIFICATIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS notifications (
    notification_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    notif_type VARCHAR(50) NOT NULL DEFAULT 'system',
    title VARCHAR(255) NOT NULL,
    message TEXT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    reference_id VARCHAR(36) NULL,
    reference_type VARCHAR(50) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (notification_id),
    INDEX ix_notifications_user_id (user_id),
    INDEX ix_notifications_created_at (created_at DESC),
    INDEX ix_notifications_unread (user_id, is_read),

    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================
-- CONVERSATIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id VARCHAR(36) NOT NULL,
    participant_1_id VARCHAR(36) NOT NULL,
    participant_2_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(36) NULL,
    last_message_text VARCHAR(500) NULL,
    last_message_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (conversation_id),
    INDEX ix_conversations_p1 (participant_1_id),
    INDEX ix_conversations_p2 (participant_2_id),
    INDEX ix_conversations_job (job_id),

    CONSTRAINT fk_conversations_p1 FOREIGN KEY (participant_1_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_conversations_p2 FOREIGN KEY (participant_2_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_conversations_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================
-- MESSAGES TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(36) NOT NULL,
    conversation_id VARCHAR(36) NOT NULL,
    sender_id VARCHAR(36) NOT NULL,
    content TEXT NULL,
    attachment_url VARCHAR(500) NULL,
    attachment_name VARCHAR(255) NULL,
    attachment_type VARCHAR(50) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (message_id),
    INDEX ix_messages_conversation (conversation_id),
    INDEX ix_messages_sender (sender_id),
    INDEX ix_messages_created_at (created_at DESC),

    CONSTRAINT fk_messages_conversation FOREIGN KEY (conversation_id)
        REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    CONSTRAINT fk_messages_sender FOREIGN KEY (sender_id)
        REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================
-- CERTIFICATIONS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS certifications (
    cert_id VARCHAR(36) NOT NULL,
    worker_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    file_url VARCHAR(500) NULL,
    rejection_reason TEXT NULL,
    reviewed_by VARCHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (cert_id),
    INDEX ix_certifications_worker (worker_id),
    INDEX ix_certifications_status (status),

    CONSTRAINT fk_certifications_worker FOREIGN KEY (worker_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_certifications_reviewer FOREIGN KEY (reviewed_by)
        REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================
-- REPORTS TABLE
-- =============================================
CREATE TABLE IF NOT EXISTS reports (
    report_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    user_name VARCHAR(255) NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NULL,
    category VARCHAR(50) NULL DEFAULT 'general',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    assigned_to VARCHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (report_id),
    INDEX ix_reports_user (user_id),
    INDEX ix_reports_status (status),
    INDEX ix_reports_priority (priority)
) ENGINE=InnoDB;

-- =============================================
-- Verification
-- =============================================
SELECT TABLE_NAME, ENGINE, TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'sanaie_db'
ORDER BY TABLE_NAME;
