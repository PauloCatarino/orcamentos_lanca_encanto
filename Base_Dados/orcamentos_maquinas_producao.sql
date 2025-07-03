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
-- Table structure for table `maquinas_producao`
--

DROP TABLE IF EXISTS `maquinas_producao`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `maquinas_producao` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome_variavel` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valor_std` decimal(10,2) DEFAULT NULL,
  `valor_serie` decimal(10,2) DEFAULT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome_variavel` (`nome_variavel`)
) ENGINE=InnoDB AUTO_INCREMENT=331 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maquinas_producao`
--

LOCK TABLES `maquinas_producao` WRITE;
/*!40000 ALTER TABLE `maquinas_producao` DISABLE KEYS */;
INSERT INTO `maquinas_producao` VALUES (1,'VALOR_SECCIONADORA',1.00,0.70,'€/ML para a máquina Seccionadora'),(2,'VALOR_ORLADORA',0.70,0.50,'€/ML para a máquina Orladora'),(3,'CNC_PRECO_PECA_BAIXO',2.00,1.00,'€/peça se AREA_M2_und ≤ 0.7'),(4,'CNC_PRECO_PECA_MEDIO',2.50,3.00,'€/peça se 0.7 < AREA_M2_und < 1'),(5,'CNC_PRECO_PECA_ALTO',3.00,6.00,'€/peça se AREA_M2_und ≥ 1'),(6,'VALOR_ABD',0.80,1.20,'€/peça para a máquina ABD'),(7,'EUROS_HORA_CNC',60.00,55.00,'€/hora para a máquina CNC'),(8,'EUROS_HORA_PRENSA',22.00,23.00,'€/hora para a máquina Prensa'),(9,'EUROS_HORA_ESQUAD',20.00,18.00,'€/hora para a máquina Esquadrejadora'),(10,'EUROS_EMBALAGEM_M3',50.00,35.00,'€/M³ para Embalagem'),(11,'EUROS_HORA_MO',22.00,17.00,'€/hora para Mão de Obra');
/*!40000 ALTER TABLE `maquinas_producao` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-03 11:16:28
