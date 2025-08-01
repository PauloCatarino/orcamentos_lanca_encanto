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
-- Table structure for table `orcamentos`
--

DROP TABLE IF EXISTS `orcamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orcamentos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `utilizador` text COLLATE utf8mb4_unicode_ci,
  `ano` varchar(4) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `num_orcamento` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `versao` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT '00',
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `nome_cliente` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enc_phc` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preco` double DEFAULT '0',
  `ref_cliente` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `obra` text COLLATE utf8mb4_unicode_ci,
  `caracteristicas` text COLLATE utf8mb4_unicode_ci,
  `localizacao` text COLLATE utf8mb4_unicode_ci,
  `info_1` text COLLATE utf8mb4_unicode_ci,
  `info_2` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `id_cliente` (`id_cliente`),
  CONSTRAINT `orcamentos_ibfk_1` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orcamentos`
--

LOCK TABLES `orcamentos` WRITE;
/*!40000 ALTER TABLE `orcamentos` DISABLE KEYS */;
INSERT INTO `orcamentos` VALUES (1,1,'Paulo','2025','250001','00','Falta Orcamentar','JF_VIVA','','30/06/2025',0,'2505063','','','','1 º teste orcamento',''),(3,2,'Andreia','2025','250002','00','Falta Orcamentar','Cicomol','','01/07/2025',0,'','','fazer orçamento + texzto','','',''),(5,1,'Paulo','2025','250001','01','Falta Orcamentar','JF_VIVA','','30/06/2025',0,'2505063','','','','1 º teste orcamento','');
/*!40000 ALTER TABLE `orcamentos` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-03 11:16:24
