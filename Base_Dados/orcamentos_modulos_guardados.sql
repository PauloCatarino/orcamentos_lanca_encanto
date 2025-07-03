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
-- Table structure for table `modulos_guardados`
--

DROP TABLE IF EXISTS `modulos_guardados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `modulos_guardados` (
  `id_modulo` int NOT NULL AUTO_INCREMENT,
  `nome_modulo` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao_modulo` text COLLATE utf8mb4_unicode_ci,
  `caminho_imagem_modulo` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_criacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `data_modificacao` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_modulo`),
  UNIQUE KEY `nome_modulo` (`nome_modulo`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modulos_guardados`
--

LOCK TABLES `modulos_guardados` WRITE;
/*!40000 ALTER TABLE `modulos_guardados` DISABLE KEYS */;
INSERT INTO `modulos_guardados` VALUES (1,'1_MOD_RP_2PORTAS_1MALEIRO_1VARAO_2PA','2 LATERAIS\n1 MALEIRO\n1 VARAO\n2 PRAT AMOVIVEIS\n2 PORTAS ABRIR','//server_le/_Lanca_Encanto/LancaEncanto/Dep._Orcamentos/Base_Dados_Orcamento/Imagens_Modulos/TIPO_5.JPG','2025-06-30 14:50:16','2025-07-01 07:43:35'),(2,'2_modulo teste 2 pa','Descricao livrre','//server_le/_Lanca_Encanto/LancaEncanto/Dep._Orcamentos/Base_Dados_Orcamento/Imagens_Modulos/TIPO_8.JPG','2025-07-01 07:45:37','2025-07-01 07:45:37'),(3,'3_lixo','',NULL,'2025-07-01 08:05:52','2025-07-01 08:05:52');
/*!40000 ALTER TABLE `modulos_guardados` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-03 11:16:15
