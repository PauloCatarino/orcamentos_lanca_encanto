-- MySQL dump 10.13  Distrib 8.0.40, for Win64 (x86_64)
--
-- Host: localhost    Database: orcamentos
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dados_modulo_medidas`
--

DROP TABLE IF EXISTS `dados_modulo_medidas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dados_modulo_medidas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ids` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `num_orc` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ver_orc` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `H` decimal(10,2) DEFAULT NULL,
  `L` decimal(10,2) DEFAULT NULL,
  `P` decimal(10,2) DEFAULT NULL,
  `H1` decimal(10,2) DEFAULT NULL,
  `L1` decimal(10,2) DEFAULT NULL,
  `P1` decimal(10,2) DEFAULT NULL,
  `H2` decimal(10,2) DEFAULT NULL,
  `L2` decimal(10,2) DEFAULT NULL,
  `P2` decimal(10,2) DEFAULT NULL,
  `H3` decimal(10,2) DEFAULT NULL,
  `L3` decimal(10,2) DEFAULT NULL,
  `P3` decimal(10,2) DEFAULT NULL,
  `H4` decimal(10,2) DEFAULT NULL,
  `L4` decimal(10,2) DEFAULT NULL,
  `P4` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=148 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dados_modulo_medidas`
--

LOCK TABLES `dados_modulo_medidas` WRITE;
/*!40000 ALTER TABLE `dados_modulo_medidas` DISABLE KEYS */;
INSERT INTO `dados_modulo_medidas` VALUES (67,'1','250001','1',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(68,'1','250002','0',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(93,'3','250001','0',2150.00,1230.00,630.00,1423.00,632.00,300.00,800.00,563.00,400.00,NULL,NULL,NULL,NULL,NULL,NULL),(104,'2','250001','0',2000.00,1200.00,600.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(119,'4','250001','0',2150.00,2100.00,650.00,2000.00,1800.00,600.00,1800.00,1500.00,580.00,1600.00,1400.00,550.00,1500.00,1000.00,400.00),(122,'1','250001','0',2000.00,1500.00,500.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(132,'4','250001','00',2500.00,1200.00,700.00,2400.00,1100.00,600.00,2300.00,1000.00,500.00,800.00,633.00,123.00,1532.00,830.00,602.00),(133,'2','250001','00',2000.00,1200.00,600.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(136,'5','250001','00',2500.00,1200.00,700.00,2400.00,1100.00,600.00,2300.00,1000.00,500.00,800.00,633.00,123.00,1532.00,830.00,602.00),(137,'1','250001','01',2300.00,800.00,600.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(144,'1','250001','00',2632.00,2531.00,653.00,2432.00,1530.00,530.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL),(147,'6','250001','00',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `dados_modulo_medidas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-06-08 23:17:45
