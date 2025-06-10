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
-- Table structure for table `dados_items_acabamentos`
--

DROP TABLE IF EXISTS `dados_items_acabamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dados_items_acabamentos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `num_orc` varchar(50) DEFAULT NULL,
  `ver_orc` varchar(10) DEFAULT NULL,
  `id_acb` varchar(50) DEFAULT NULL,
  `linha` int DEFAULT NULL,
  `material` text,
  `descricao` text,
  `ref_le` text,
  `descricao_no_orcamento` text,
  `ptab` double DEFAULT NULL,
  `pliq` double DEFAULT NULL,
  `desc1_plus` double DEFAULT NULL,
  `desc2_minus` double DEFAULT NULL,
  `und` text,
  `desp` double DEFAULT NULL,
  `corres_orla_0_4` text,
  `corres_orla_1_0` text,
  `tipo` text,
  `familia` text,
  `comp_mp` double DEFAULT NULL,
  `larg_mp` double DEFAULT NULL,
  `esp_mp` double DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `num_orc` (`num_orc`,`ver_orc`,`id_acb`,`linha`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dados_items_acabamentos`
--

LOCK TABLES `dados_items_acabamentos` WRITE;
/*!40000 ALTER TABLE `dados_items_acabamentos` DISABLE KEYS */;
INSERT INTO `dados_items_acabamentos` VALUES (13,'250001','00','3',0,'Acab_Lacar','','ACB0001','LACAR 1 FACE',25,25.46,0.05,0.03,'M2',0.05,'','','LACAR','ACABAMENTOS',0,0,0),(14,'250001','00','3',1,'Acab_Verniz','','ACB0001','LACAR 1 FACE',15,15,0,0,'M2',0.05,'','','LACAR','ACABAMENTOS',0,0,0),(15,'250001','00','3',2,'Acab_Face_1','','','',0,0,0,0,'',0,'','','LACAR','ACABAMENTOS',0,0,0),(16,'250001','00','3',3,'Acab_Face_2','','','',0,0,0,0,'',0,'','','LACAR','ACABAMENTOS',0,0,0),(17,'250001','00','1',0,'Acab_Lacar_Face_Sup',NULL,'ACB0001','LACAR 1 FACE',25,25.46,0.05,0.03,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0),(18,'250001','00','1',1,'Acab_Lacar_Face_Inf',NULL,'ACB0001','LACAR 1 FACE',15,15,0,0,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0),(19,'250001','00','1',2,'Acab_Verniz_Face_Sup',NULL,NULL,NULL,0,0,0,0,NULL,0,NULL,NULL,NULL,NULL,0,0,0),(20,'250001','00','1',3,'Acab_Verniz_Face_Inf',NULL,NULL,NULL,0,0,0,0,NULL,0,NULL,NULL,NULL,NULL,0,0,0),(29,'250001','00','6',0,'Acab_Lacar_Face_Sup','laca sp','ACB0001','LACAR 1 FACE',25,25.46,0.05,0.03,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0),(30,'250001','00','6',1,'Acab_Lacar_Face_Inf','laca inf','ACB0001','LACAR 1 FACE',15,15,0,0,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0),(31,'250001','00','6',2,'Acab_Verniz_Face_Sup','verniz sup','ACB0001','LACAR 1 FACE',25,25.46,0.05,0.03,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0),(32,'250001','00','6',3,'Acab_Verniz_Face_Inf','verniz inf','ACB0001','LACAR 1 FACE',25,25.46,0.05,0.03,'M2',0.05,NULL,NULL,NULL,NULL,0,0,0);
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

-- Dump completed on 2025-06-08 23:17:44
