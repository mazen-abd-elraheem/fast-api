CREATE DATABASE IF NOT EXISTS `sanaie_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `sanaie_db`;

-- ------------------------------------------------------
-- Table structure for table `alembic_version`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `users`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `phone_number` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  `skills` json DEFAULT NULL,
  `profile_image_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_available` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'available',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `is_verified` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'unverified',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `admin_audit_logs`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `admin_audit_logs`;
CREATE TABLE `admin_audit_logs` (
  `log_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `admin_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `details` json DEFAULT NULL,
  `severity` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`log_id`),
  KEY `ix_admin_audit_logs_action` (`action`),
  KEY `ix_admin_audit_logs_admin_id` (`admin_id`),
  KEY `ix_admin_audit_logs_log_id` (`log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `jobs`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `jobs`;
CREATE TABLE `jobs` (
  `job_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `client_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `image_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `initial_price` decimal(10,2) NOT NULL,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  `address` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_worker_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`job_id`),
  KEY `assigned_worker_id` (`assigned_worker_id`),
  KEY `ix_jobs_client_id` (`client_id`),
  KEY `ix_jobs_job_id` (`job_id`),
  CONSTRAINT `jobs_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `jobs_ibfk_2` FOREIGN KEY (`assigned_worker_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `bids`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `bids`;
CREATE TABLE `bids` (
  `bid_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `job_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `worker_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `scheduled_at` datetime DEFAULT NULL,
  `counter_amount` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`bid_id`),
  KEY `ix_bids_job_id` (`job_id`),
  KEY `ix_bids_bid_id` (`bid_id`),
  KEY `ix_bids_worker_id` (`worker_id`),
  CONSTRAINT `bids_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE CASCADE,
  CONSTRAINT `bids_ibfk_2` FOREIGN KEY (`worker_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `certifications`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `certifications`;
CREATE TABLE `certifications` (
  `cert_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `worker_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rejection_reason` text COLLATE utf8mb4_unicode_ci,
  `reviewed_by` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`cert_id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `ix_certifications_worker_id` (`worker_id`),
  KEY `ix_certifications_cert_id` (`cert_id`),
  CONSTRAINT `certifications_ibfk_1` FOREIGN KEY (`worker_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `certifications_ibfk_2` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `contractor_groups`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `contractor_groups`;
CREATE TABLE `contractor_groups` (
  `contractor_group_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contractor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `technician_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `joined_at` datetime NOT NULL,
  `removed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`contractor_group_id`),
  KEY `ix_contractor_groups_contractor_group_id` (`contractor_group_id`),
  KEY `ix_contractor_groups_contractor_id` (`contractor_id`),
  KEY `ix_contractor_groups_technician_id` (`technician_id`),
  CONSTRAINT `contractor_groups_ibfk_1` FOREIGN KEY (`contractor_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `contractor_groups_ibfk_2` FOREIGN KEY (`technician_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `conversations`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `conversations`;
CREATE TABLE `conversations` (
  `conversation_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `participant_1_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `participant_2_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `job_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_message_text` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_message_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`conversation_id`),
  KEY `ix_conversations_job_id` (`job_id`),
  KEY `ix_conversations_conversation_id` (`conversation_id`),
  KEY `ix_conversations_participant_1_id` (`participant_1_id`),
  KEY `ix_conversations_participant_2_id` (`participant_2_id`),
  CONSTRAINT `conversations_ibfk_1` FOREIGN KEY (`participant_1_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `conversations_ibfk_2` FOREIGN KEY (`participant_2_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `conversations_ibfk_3` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `id_verifications`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `id_verifications`;
CREATE TABLE `id_verifications` (
  `verification_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `front_image_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `back_image_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rejection_reason` text COLLATE utf8mb4_unicode_ci,
  `reviewed_by` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`verification_id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `ix_id_verifications_verification_id` (`verification_id`),
  KEY `ix_id_verifications_user_id` (`user_id`),
  CONSTRAINT `id_verifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `id_verifications_ibfk_2` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `job_assignments`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `job_assignments`;
CREATE TABLE `job_assignments` (
  `assignment_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contractor_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `technician_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `job_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `latitude` float DEFAULT NULL,
  `longitude` float DEFAULT NULL,
  `address` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `completed_at` datetime DEFAULT NULL,
  `duration_minutes` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`assignment_id`),
  KEY `ix_job_assignments_assignment_id` (`assignment_id`),
  KEY `ix_job_assignments_contractor_id` (`contractor_id`),
  KEY `ix_job_assignments_job_id` (`job_id`),
  KEY `ix_job_assignments_technician_id` (`technician_id`),
  CONSTRAINT `job_assignments_ibfk_1` FOREIGN KEY (`contractor_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `job_assignments_ibfk_2` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE SET NULL,
  CONSTRAINT `job_assignments_ibfk_3` FOREIGN KEY (`technician_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `messages`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `messages`;
CREATE TABLE `messages` (
  `message_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `conversation_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` text COLLATE utf8mb4_unicode_ci,
  `attachment_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attachment_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attachment_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`message_id`),
  KEY `ix_messages_conversation_id` (`conversation_id`),
  KEY `ix_messages_sender_id` (`sender_id`),
  KEY `ix_messages_message_id` (`message_id`),
  CONSTRAINT `messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`conversation_id`),
  CONSTRAINT `messages_ibfk_2` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `notifications`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `notification_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `notif_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci,
  `is_read` tinyint(1) NOT NULL,
  `reference_id` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reference_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `ix_notifications_user_id` (`user_id`),
  KEY `ix_notifications_notification_id` (`notification_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `reports`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `reports`;
CREATE TABLE `reports` (
  `report_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `category` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `priority` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `assigned_to` varchar(36) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`report_id`),
  KEY `ix_reports_user_id` (`user_id`),
  KEY `ix_reports_report_id` (`report_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------
-- Table structure for table `reviews`
-- ------------------------------------------------------

DROP TABLE IF EXISTS `reviews`;
CREATE TABLE `reviews` (
  `review_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `job_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `client_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `worker_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `rating_score` int NOT NULL,
  `comment` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`review_id`),
  UNIQUE KEY `ix_reviews_job_id` (`job_id`),
  KEY `ix_reviews_client_id` (`client_id`),
  KEY `ix_reviews_worker_id` (`worker_id`),
  KEY `ix_reviews_review_id` (`review_id`),
  CONSTRAINT `reviews_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`job_id`) ON DELETE CASCADE,
  CONSTRAINT `reviews_ibfk_2` FOREIGN KEY (`client_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `reviews_ibfk_3` FOREIGN KEY (`worker_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `ck_rating_range` CHECK (((`rating_score` >= 1) and (`rating_score` <= 5)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
