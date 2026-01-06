CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;

CREATE TABLE IF NOT EXISTS patient (
  pat_id INT AUTO_INCREMENT PRIMARY KEY,
  pat_first_name VARCHAR(100) NOT NULL,
  pat_last_name VARCHAR(100) NOT NULL,
  pat_insurance_no VARCHAR(100) NOT NULL,
  pat_ph_no VARCHAR(30) NOT NULL,
  pat_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  pat_address VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS doctor (
  doc_id INT AUTO_INCREMENT PRIMARY KEY,
  doc_first_name VARCHAR(100) NOT NULL,
  doc_last_name VARCHAR(100) NOT NULL,
  doc_ph_no VARCHAR(30) NOT NULL,
  doc_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  doc_address VARCHAR(255) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS appointment (
  app_id INT AUTO_INCREMENT PRIMARY KEY,
  pat_id INT NOT NULL,
  doc_id INT NOT NULL,
  appointment_date DATE NOT NULL,
  CONSTRAINT fk_appointment_patient
    FOREIGN KEY (pat_id) REFERENCES patient(pat_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_appointment_doctor
    FOREIGN KEY (doc_id) REFERENCES doctor(doc_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;


CREATE TABLE `triage_analysis` (
  `triage_id` int(11) NOT NULL,
  `pat_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `label` varchar(50) NOT NULL,
  `pred` varchar(10) NOT NULL,
  `payload_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payload_json`)),
  `proba_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`proba_json`)),
  `input_used_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`input_used_json`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
