-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: orcamentos
-- ------------------------------------------------------
-- Server version	8.0.42

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
-- Table structure for table `dados_items_acabamentos`
--

DROP TABLE IF EXISTS `dados_items_acabamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dados_items_acabamentos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `num_orc` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ver_orc` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_acb` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `linha` int NOT NULL,
  `material` text COLLATE utf8mb4_unicode_ci,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ref_le` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descricao_no_orcamento` text COLLATE utf8mb4_unicode_ci,
  `ptab` double DEFAULT '0',
  `pliq` double DEFAULT '0',
  `desc1_plus` double DEFAULT '0',
  `desc2_minus` double DEFAULT '0',
  `und` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `desp` double DEFAULT '0',
  `corres_orla_0_4` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `corres_orla_1_0` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tipo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `familia` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_mp` double DEFAULT '0',
  `larg_mp` double DEFAULT '0',
  `esp_mp` double DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_item_acb_unico` (`num_orc`,`ver_orc`,`id_acb`,`linha`),
  KEY `idx_item_acb_lookup` (`num_orc`,`ver_orc`,`id_acb`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dados_items_acabamentos`
--

LOCK TABLES `dados_items_acabamentos` WRITE;
/*!40000 ALTER TABLE `dados_items_acabamentos` DISABLE KEYS */;
INSERT INTO `dados_items_acabamentos` VALUES (1,'250001','00','1',0,'Acab_Lacar_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(2,'250001','00','1',1,'Acab_Lacar_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(3,'250001','00','1',2,'Acab_Verniz_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(4,'250001','00','1',3,'Acab_Verniz_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(5,'250002','00','1',0,'Acab_Lacar_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(6,'250002','00','1',1,'Acab_Lacar_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(7,'250002','00','1',2,'Acab_Verniz_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(8,'250002','00','1',3,'Acab_Verniz_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(9,'250002','00','2',0,'Acab_Lacar_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(10,'250002','00','2',1,'Acab_Lacar_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(11,'250002','00','2',2,'Acab_Verniz_Face_Sup',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL),(12,'250002','00','2',3,'Acab_Verniz_Face_Inf',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'ACABAMENTOS',NULL,NULL,NULL);
/*!40000 ALTER TABLE `dados_items_acabamentos` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-03 11:16:26
