-- HemoTrack backup before migration

CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `doctors` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `specialization` varchar(255) DEFAULT NULL,
  `phone` varchar(30) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `clinic_address` text,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_doctors_id` (`id`),
  KEY `ix_doctors_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `patients` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `gender` enum('male','female','other') NOT NULL,
  `age_years` int NOT NULL DEFAULT '0',
  `age_months` int NOT NULL DEFAULT '0',
  `age_days` int NOT NULL DEFAULT '0',
  `patient_type` enum('OTHER','OPD','IPD') NOT NULL DEFAULT 'OTHER',
  `phone` varchar(30) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `address` text,
  `collection_date` date DEFAULT NULL,
  `received_date` date DEFAULT NULL,
  `reporting_date` date DEFAULT NULL,
  `referred_by_doctor_id` int DEFAULT NULL,
  `agent_or_collection_centre` varchar(255) DEFAULT NULL,
  `remarks` text,
  `is_cancelled` tinyint(1) NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_by` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_patients_created_by` (`created_by`),
  KEY `ix_patients_id` (`id`),
  KEY `ix_patients_name` (`name`),
  KEY `ix_patients_referred_by_doctor_id` (`referred_by_doctor_id`),
  CONSTRAINT `patients_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `patients_ibfk_2` FOREIGN KEY (`referred_by_doctor_id`) REFERENCES `doctors` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `phone` varchar(30) DEFAULT NULL,
  `role` enum('admin','receptionist','lab_technician','lab_manager') NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- DATA: alembic_version
INSERT INTO alembic_version VALUES ('001_initial');

-- DATA: doctors

-- DATA: patients

-- DATA: users
INSERT INTO users VALUES (1,'admin@hemotrack.com','$2b$12$DNkh9duPQIx8Jl9w67XM5Oa53O9C7odGN04/1BVBipfBF9kSLVvSS','System Admin',NULL,'admin',1,datetime.datetime(2026, 9, 30, 18, 19, 12),datetime.datetime(2026, 9, 30, 18, 19, 12));

