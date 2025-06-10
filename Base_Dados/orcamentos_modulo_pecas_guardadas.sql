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
-- Table structure for table `modulo_pecas_guardadas`
--

DROP TABLE IF EXISTS `modulo_pecas_guardadas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `modulo_pecas_guardadas` (
  `id_modulo_peca` int NOT NULL AUTO_INCREMENT,
  `id_modulo_fk` int NOT NULL,
  `ordem_peca` int NOT NULL,
  `descricao_livre_peca` text COLLATE utf8mb4_unicode_ci,
  `def_peca_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qt_und_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `larg_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `esp_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mat_default_peca` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tab_default_peca` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grupo_peca` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `und_peca` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_ass_1_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_ass_2_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_ass_3_peca` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_modulo_peca`),
  KEY `id_modulo_fk` (`id_modulo_fk`),
  CONSTRAINT `modulo_pecas_guardadas_ibfk_1` FOREIGN KEY (`id_modulo_fk`) REFERENCES `modulos_guardados` (`id_modulo`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modulo_pecas_guardadas`
--

LOCK TABLES `modulo_pecas_guardadas` WRITE;
/*!40000 ALTER TABLE `modulo_pecas_guardadas` DISABLE KEYS */;
INSERT INTO `modulo_pecas_guardadas` VALUES (1,1,0,'','MODULO','','H/2','L/2','P','','','','','','',''),(2,1,1,'','TETO [2222]','2','LM','PM','30.0','Mat_Tetos','Tab_Material_11','','M2','','',''),(3,1,2,'','LATERAL [2222]','2','HM','PM','19.0','Mat_Laterais','Tab_Material_11','','M2','','',''),(4,1,3,'','COSTA CHAPAR [0000]','1','HM','PM','10.0','Mat_Costas','Tab_Material_11','','M2','','',''),(5,1,4,'','PORTA ABRIR [2222] + DOBRADICA','2','HM','LM/2','19.0','Mat_Portas_Abrir','Tab_Material_11','','M2','DOBRADICA','',''),(6,1,5,'','DOBRADICA','3','','','0.0','Fer_Dobradica','Tab_Ferragens_11','','UND','','',''),(7,1,6,'','','','','','','','','','','','',''),(8,1,7,'','','','','','','','','','','','',''),(9,2,0,'','','','','','','','','','','','',''),(10,2,1,'','PORTA ABRIR [2222] + DOBRADICA','2','H','L/2','19.0','Mat_Portas_Abrir','Tab_Material_11','caixote','M2','DOBRADICA','',''),(11,2,2,'','DOBRADICA','4','','','0.0','Fer_Dobradica','Tab_Ferragens_11','ferragens','UND','','',''),(12,2,3,'','','','','','','','','','','','','');
/*!40000 ALTER TABLE `modulo_pecas_guardadas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-06-08 23:17:46
