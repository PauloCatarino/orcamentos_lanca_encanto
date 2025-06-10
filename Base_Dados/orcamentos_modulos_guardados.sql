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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modulos_guardados`
--

LOCK TABLES `modulos_guardados` WRITE;
/*!40000 ALTER TABLE `modulos_guardados` DISABLE KEYS */;
INSERT INTO `modulos_guardados` VALUES (1,'1_Mod_2_Portas','Modulo 2 laterais + costa  2 portas caixote simples','C:/Users/Utilizador/Documents/ORCAMENTOS_LE_V2/Base_Dados_Orcamento/Imagens_Modulos/Inf_Cozinha_4_GVT.jpg','2025-05-18 18:46:45','2025-05-18 18:46:45'),(2,'Porta_com_Dobradica','Porta com dobradica inlcuida','C:/Users/Utilizador/Documents/ORCAMENTOS_LE_V2/Base_Dados_Orcamento/Imagens_Modulos/Porta_Dobradica.jpg','2025-05-18 21:24:03','2025-05-18 21:24:03');
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

-- Dump completed on 2025-06-08 23:17:47
