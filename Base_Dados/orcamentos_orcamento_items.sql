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
-- Table structure for table `orcamento_items`
--

DROP TABLE IF EXISTS `orcamento_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orcamento_items` (
  `id_item` int NOT NULL AUTO_INCREMENT,
  `id_orcamento` int NOT NULL,
  `item` text COLLATE utf8mb4_unicode_ci,
  `codigo` text COLLATE utf8mb4_unicode_ci,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `altura` double DEFAULT '0',
  `largura` double DEFAULT '0',
  `profundidade` double DEFAULT '0',
  `und` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qt` double DEFAULT '1',
  `preco_unitario` double DEFAULT '0',
  `preco_total` double DEFAULT '0',
  `custo_produzido` double DEFAULT '0',
  `custo_total_orlas` double DEFAULT '0',
  `custo_total_mao_obra` double DEFAULT '0',
  `custo_total_materia_prima` double DEFAULT '0',
  `custo_total_acabamentos` double DEFAULT '0',
  `margem_lucro_perc` double DEFAULT '0',
  `valor_margem` double DEFAULT '0',
  `custos_admin_perc` double DEFAULT '0',
  `valor_custos_admin` double DEFAULT '0',
  `ajustes1_perc` double DEFAULT '0',
  `valor_ajustes1` double DEFAULT '0',
  `ajustes2_perc` double DEFAULT '0',
  `valor_ajustes2` double DEFAULT '0',
  PRIMARY KEY (`id_item`),
  KEY `id_orcamento` (`id_orcamento`),
  CONSTRAINT `orcamento_items_ibfk_1` FOREIGN KEY (`id_orcamento`) REFERENCES `orcamentos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orcamento_items`
--

LOCK TABLES `orcamento_items` WRITE;
/*!40000 ALTER TABLE `orcamento_items` DISABLE KEYS */;
INSERT INTO `orcamento_items` VALUES (1,2,'1','RP_01','roupeiro 3 portas',2500,1800,600,'und',1,1025.981775,1025.981775,835.15,5.12,40.51,789.52,0,0.1285,107.31677499999999,0.05,41.7575,0.03,25.054499999999997,0.02,16.703),(2,2,'2','RP_02','roupeiro 4 portas',2300,2000,580,'und',2,879.4831499999999,1758.9662999999998,715.9,22.65,55.12,638.13,0,0.1285,91.99315,0.05,35.795,0.03,21.476999999999997,0.02,14.318),(3,2,'3','RP_03','roupeiro 2 portas',2300,1000,630,'und',3,578.906055,1736.7181650000002,471.23,4.74,23.37,443.12,0,0.1285,60.553055,0.05,23.561500000000002,0.03,14.1369,0.02,9.4246),(5,4,'1','RP_01','roupeiro 3 portas',2500,1800,600,'und',1,0,0,0,0,0,0,0,0.1,0,0.05,0,0.03,0,0.02,0),(6,2,'4','RP_04','roupeiro 1 portas',2300,500,630,'und',1,1257.726015,1257.726015,1023.7900000000001,10.82,38.51,974.46,0,0.1285,131.557015,0.05,51.18950000000001,0.03,30.713700000000003,0.02,20.475800000000003),(12,2,'5','RP_04','roupeiro 1 portas novo duplicado',2300,500,630,'und',1,1257.726015,1257.726015,1023.7900000000001,10.82,38.51,974.46,0,0.1285,131.557015,0.05,51.18950000000001,0.03,30.713700000000003,0.02,20.475800000000003),(13,4,'2','RP_01','roupeiro 32 portas',2500,1000,600,'und',2,0,0,0,0,0,0,0,0.15,0,0.05,0,0.03,0,0.02,0),(14,2,'6','RP_05','ROUPEIRO 4 PORTAS ABRIR',2500,1800,603,'und',1,347.07499999999993,347.07499999999993,277.65999999999997,3.12,36.05,122.02,116.47,0.15,41.648999999999994,0.05,13.883,0.03,8.329799999999999,0.02,5.5531999999999995);
/*!40000 ALTER TABLE `orcamento_items` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-06-08 23:17:48
