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
-- Table structure for table `orcamento_maquinas`
--

DROP TABLE IF EXISTS `orcamento_maquinas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orcamento_maquinas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `numero_orcamento` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `versao_orcamento` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `descricao_equipamento` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valor_producao_std` decimal(10,2) DEFAULT NULL,
  `valor_producao_serie` decimal(10,2) DEFAULT NULL,
  `resumo_descricao` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_orcamento_maq` (`numero_orcamento`,`versao_orcamento`,`descricao_equipamento`)
) ENGINE=InnoDB AUTO_INCREMENT=672 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orcamento_maquinas`
--

LOCK TABLES `orcamento_maquinas` WRITE;
/*!40000 ALTER TABLE `orcamento_maquinas` DISABLE KEYS */;
INSERT INTO `orcamento_maquinas` VALUES (1,'250001','01','VALOR_SECCIONADORA',1.00,0.50,'€/ML para a máquina Seccionadora'),(2,'250001','01','VALOR_ORLADORA',0.70,0.40,'€/ML para a máquina Orladora'),(3,'250001','01','CNC_PRECO_PECA_BAIXO',2.00,1.50,'€/peça se AREA_M2_und ≤ 0.7'),(4,'250001','01','CNC_PRECO_PECA_MEDIO',2.50,2.00,'€/peça se 0.7 < AREA_M2_und < 1'),(5,'250001','01','CNC_PRECO_PECA_ALTO',3.00,2.50,'€/peça se AREA_M2_und ≥ 1'),(6,'250001','01','VALOR_ABD',0.80,0.60,'€/peça para a máquina ABD'),(7,'250001','01','EUROS_HORA_CNC',60.00,48.00,'€/hora para a máquina CNC'),(8,'250001','01','EUROS_HORA_PRENSA',22.00,17.00,'€/hora para a máquina Prensa'),(9,'250001','01','EUROS_HORA_ESQUAD',20.00,15.00,'€/hora para a máquina Esquadrejadora'),(10,'250001','01','EUROS_EMBALAGEM_M3',50.00,35.00,'€/M³ para Embalagem'),(11,'250001','01','EUROS_HORA_MO',22.00,17.00,'€/hora para Mão de Obra'),(34,'250001','00','VALOR_SECCIONADORA',1.00,0.70,'€/ML para a máquina Seccionadora'),(35,'250001','00','VALOR_ORLADORA',0.70,0.50,'€/ML para a máquina Orladora'),(36,'250001','00','CNC_PRECO_PECA_BAIXO',2.00,1.00,'€/peça se AREA_M2_und ≤ 0.7'),(37,'250001','00','CNC_PRECO_PECA_MEDIO',2.50,3.00,'€/peça se 0.7 < AREA_M2_und < 1'),(38,'250001','00','CNC_PRECO_PECA_ALTO',3.00,6.00,'€/peça se AREA_M2_und ≥ 1'),(39,'250001','00','VALOR_ABD',0.80,1.20,'€/peça para a máquina ABD'),(40,'250001','00','EUROS_HORA_CNC',60.00,55.00,'€/hora para a máquina CNC'),(41,'250001','00','EUROS_HORA_PRENSA',22.00,23.00,'€/hora para a máquina Prensa'),(42,'250001','00','EUROS_HORA_ESQUAD',20.00,18.00,'€/hora para a máquina Esquadrejadora'),(43,'250001','00','EUROS_EMBALAGEM_M3',50.00,35.00,'€/M³ para Embalagem'),(44,'250001','00','EUROS_HORA_MO',22.00,17.00,'€/hora para Mão de Obra'),(56,'250002','00','VALOR_SECCIONADORA',1.00,0.70,'€/ML para a máquina Seccionadora'),(57,'250002','00','VALOR_ORLADORA',0.70,0.50,'€/ML para a máquina Orladora'),(58,'250002','00','CNC_PRECO_PECA_BAIXO',2.00,1.50,'€/peça se AREA_M2_und ≤ 0.7'),(59,'250002','00','CNC_PRECO_PECA_MEDIO',2.50,2.00,'€/peça se 0.7 < AREA_M2_und < 1'),(60,'250002','00','CNC_PRECO_PECA_ALTO',3.00,2.50,'€/peça se AREA_M2_und ≥ 1'),(61,'250002','00','VALOR_ABD',0.80,0.60,'€/peça para a máquina ABD'),(62,'250002','00','EUROS_HORA_CNC',60.00,48.00,'€/hora para a máquina CNC'),(63,'250002','00','EUROS_HORA_PRENSA',22.00,17.00,'€/hora para a máquina Prensa'),(64,'250002','00','EUROS_HORA_ESQUAD',20.00,15.00,'€/hora para a máquina Esquadrejadora'),(65,'250002','00','EUROS_EMBALAGEM_M3',50.00,35.00,'€/M³ para Embalagem'),(66,'250002','00','EUROS_HORA_MO',22.00,17.00,'€/hora para Mão de Obra');
/*!40000 ALTER TABLE `orcamento_maquinas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-03 11:16:05
