/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.4.12-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: minchodan_db
-- ------------------------------------------------------
-- Server version	11.4.12-MariaDB-ubu2404

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `admin_accounts`
--

DROP TABLE IF EXISTS `admin_accounts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_accounts` (
  `admin_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `employee_no` varchar(50) NOT NULL,
  `name` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(11) NOT NULL DEFAULT 'operator',
  `status` varchar(8) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `UK_ADMIN_ACCOUNTS_EMPLOYEE_NO` (`employee_no`),
  KEY `IDX_ADMIN_ACCOUNTS_ROLE` (`role`),
  CONSTRAINT `admin_role` CHECK (`role` in ('super_admin','operator','viewer')),
  CONSTRAINT `admin_account_status` CHECK (`status` in ('active','inactive','locked','deleted'))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_accounts`
--

LOCK TABLES `admin_accounts` WRITE;
/*!40000 ALTER TABLE `admin_accounts` DISABLE KEYS */;
INSERT INTO `admin_accounts` VALUES
(1,'EMP001','시스템 관리자','$2b$12$eImiTXuWVxfM37uY4JANjQ==','super_admin','active'),
(2,'EMP002','운영 담당자','$2b$12$eImiTXuWVxfM37uY4JANjQ==','operator','active');
/*!40000 ALTER TABLE `admin_accounts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `admin_login_audits`
--

DROP TABLE IF EXISTS `admin_login_audits`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_login_audits` (
  `audit_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `employee_no` varchar(50) NOT NULL,
  `success` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`audit_id`),
  KEY `IDX_ADMIN_LOGIN_AUDITS_EMPLOYEE_NO` (`employee_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin_login_audits`
--

LOCK TABLES `admin_login_audits` WRITE;
/*!40000 ALTER TABLE `admin_login_audits` DISABLE KEYS */;
/*!40000 ALTER TABLE `admin_login_audits` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `app_users`
--

DROP TABLE IF EXISTS `app_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_users` (
  `user_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `phone` varchar(30) NOT NULL,
  `disability_severity` varchar(30) NOT NULL,
  `birth_date` date DEFAULT NULL,
  `guardian_phone` varchar(30) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `status` varchar(8) NOT NULL DEFAULT 'active',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `UK_APP_USERS_PHONE` (`phone`),
  KEY `IDX_APP_USERS_DISABILITY_SEVERITY` (`disability_severity`),
  KEY `IDX_APP_USERS_STATUS` (`status`),
  CONSTRAINT `user_status` CHECK (`status` in ('active','inactive','deleted'))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `app_users`
--

LOCK TABLES `app_users` WRITE;
/*!40000 ALTER TABLE `app_users` DISABLE KEYS */;
INSERT INTO `app_users` VALUES
(1,'홍길동','010-1234-5678','severe','1990-01-01','010-9876-5432','서울시 강남구','active'),
(2,'김철수','010-1111-2222','mild','1985-05-05','010-3333-4444','서울시 서초구','active');
/*!40000 ALTER TABLE `app_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detection_guidance_logs`
--

DROP TABLE IF EXISTS `detection_guidance_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `detection_guidance_logs` (
  `log_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `event_id` varchar(64) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `device_id` bigint(20) DEFAULT NULL,
  `detected_at` datetime NOT NULL,
  `stream_type` varchar(9) NOT NULL DEFAULT 'unknown',
  `detected_objects_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`detected_objects_json`)),
  `tts_text` text NOT NULL,
  `frame_path` varchar(255) DEFAULT NULL,
  `false_positive` tinyint(1) DEFAULT NULL,
  `latency_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`latency_json`)),
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`log_id`),
  UNIQUE KEY `UK_DETECTION_GUIDANCE_LOGS_EVENT_ID` (`event_id`),
  KEY `IDX_DETECTION_GUIDANCE_LOGS_DEVICE_ID` (`device_id`),
  KEY `IDX_DETECTION_GUIDANCE_LOGS_USER_ID` (`user_id`),
  KEY `IDX_DETECTION_GUIDANCE_LOGS_STREAM_TYPE` (`stream_type`),
  KEY `IDX_DETECTION_GUIDANCE_LOGS_DETECTED_AT` (`detected_at`),
  CONSTRAINT `detection_guidance_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `app_users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `detection_guidance_logs_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `user_devices` (`device_id`) ON DELETE SET NULL,
  CONSTRAINT `stream_type` CHECK (`stream_type` in ('reflex','cognitive','unknown'))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detection_guidance_logs`
--

LOCK TABLES `detection_guidance_logs` WRITE;
/*!40000 ALTER TABLE `detection_guidance_logs` DISABLE KEYS */;
INSERT INTO `detection_guidance_logs` VALUES
(1,'EVT-0001',1,1,'2026-07-15 13:02:37','cognitive','{\"objects\": [\"bollard\"]}','전방에 볼라드가 있습니다. 주의하세요.',NULL,0,NULL,'2026-07-15 13:02:37');
/*!40000 ALTER TABLE `detection_guidance_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_devices`
--

DROP TABLE IF EXISTS `user_devices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_devices` (
  `device_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `device_uuid` varchar(100) NOT NULL,
  `platform` varchar(7) NOT NULL DEFAULT 'unknown',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `UK_USER_DEVICES_DEVICE_UUID` (`device_uuid`),
  KEY `IDX_USER_DEVICES_USER_ID` (`user_id`),
  CONSTRAINT `user_devices_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `app_users` (`user_id`),
  CONSTRAINT `device_platform` CHECK (`platform` in ('ios','android','unknown'))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_devices`
--

LOCK TABLES `user_devices` WRITE;
/*!40000 ALTER TABLE `user_devices` DISABLE KEYS */;
INSERT INTO `user_devices` VALUES
(1,1,'dev-001','android',1),
(2,2,'dev-002','ios',1);
/*!40000 ALTER TABLE `user_devices` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-07-15 13:06:07
