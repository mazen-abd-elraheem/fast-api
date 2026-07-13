-- =============================================
-- Sanaie Platform — Migration: v1.0 → v2.0
-- Run this against your existing sanaie_db
-- =============================================

USE sanaie_db;

-- =============================================
-- USERS TABLE
-- =============================================

-- Step 1: Convert existing comma-separated skills to JSON arrays
UPDATE users SET skills = NULL WHERE skills IS NOT NULL AND skills = '';
UPDATE users SET skills = CONCAT('["', REPLACE(skills, ',', '","'), '"]') WHERE skills IS NOT NULL;

-- Step 2: Now safely change column type to JSON
ALTER TABLE users MODIFY COLUMN skills JSON NULL;

-- Add worker availability status
ALTER TABLE users ADD COLUMN is_available VARCHAR(20) NOT NULL DEFAULT 'available' AFTER profile_image_url;

-- Add admin to role enum
ALTER TABLE users MODIFY COLUMN role ENUM('client', 'worker', 'admin') NOT NULL DEFAULT 'client';

-- Add location index for geo queries
CREATE INDEX ix_users_location ON users (latitude, longitude);

-- =============================================
-- JOBS TABLE
-- =============================================

-- Change initial_price from DOUBLE to DECIMAL
ALTER TABLE jobs MODIFY COLUMN initial_price DECIMAL(10, 2) NOT NULL;

-- Add job location fields
ALTER TABLE jobs ADD COLUMN latitude DOUBLE NULL AFTER initial_price;
ALTER TABLE jobs ADD COLUMN longitude DOUBLE NULL AFTER latitude;
ALTER TABLE jobs ADD COLUMN address VARCHAR(500) NULL AFTER longitude;

-- Add fulltext index for search
ALTER TABLE jobs ADD FULLTEXT INDEX ft_jobs_search (title, description);

-- =============================================
-- BIDS TABLE
-- =============================================

-- Change amount from DOUBLE to DECIMAL
ALTER TABLE bids MODIFY COLUMN amount DECIMAL(10, 2) NOT NULL;

-- Add message/proposal field
ALTER TABLE bids ADD COLUMN message TEXT NULL AFTER amount;

-- =============================================
-- Done
-- =============================================
SELECT 'Migration v1 → v2 complete!' AS status;
