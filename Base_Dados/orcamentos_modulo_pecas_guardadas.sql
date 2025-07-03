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
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modulo_pecas_guardadas`
--

LOCK TABLES `modulo_pecas_guardadas` WRITE;
/*!40000 ALTER TABLE `modulo_pecas_guardadas` DISABLE KEYS */;
INSERT INTO `modulo_pecas_guardadas` VALUES (15,1,0,'','','','','','','','','','','','',''),(16,1,1,'','MODULO','','H','L/2','P','','','','','','',''),(17,1,2,'','COSTA CHAPAR [0000]','1','HM','LM','10.0','Mat_Costas','Tab_Material_11','','M2','','',''),(18,1,3,'','LATERAL [2022]','2','HM','PM','19.0','Mat_Laterais','Tab_Material_11','','M2','','',''),(19,1,4,'','TETO [2000]','1','LM','PM','19.0','Mat_Tetos','Tab_Material_11','','M2','','',''),(20,1,5,'','FUNDO [2000] + PES_1','1','LM','PM','19.0','Mat_Fundos','Tab_Material_11','','M2','PES_1','',''),(21,1,6,'','PES_1','6','','','100.0','Fer_Pes_2','Tab_Ferragens_11','','UND','','',''),(22,1,7,'','','','','','','','','','','','',''),(23,2,0,'','','','','','','','','','','','',''),(24,2,1,'','MODULO','','H','L/2','P','','','','','','',''),(25,2,2,'','COSTA CHAPAR [0000]','1','HM','LM','10.0','Mat_Costas','Tab_Material_11','','M2','','',''),(26,2,3,'','LATERAL [2022]','2','HM','PM','19.0','Mat_Laterais','Tab_Material_11','','M2','','',''),(27,2,4,'','TETO [2000]','1','LM','PM','19.0','Mat_Tetos','Tab_Material_11','','M2','','',''),(28,2,5,'','FUNDO [2000] + PES_1','1','LM','PM','19.0','Mat_Fundos','Tab_Material_11','','M2','PES_1','',''),(29,2,6,'','PES_1','6','','','100.0','Fer_Pes_2','Tab_Ferragens_11','','UND','','',''),(30,2,7,'','','','','','','','','','','','',''),(31,2,8,'','PRATELEIRA AMOVIVEL [2111] + VARAO + SUPORTE VARAO','1','LM','PM','19.0','Mat_Prat_Amoviveis','Tab_Material_11','caixote','M2','VARAO ROUPEIRO','SUPORTE VARAO',''),(32,2,9,'','VARAO ROUPEIRO','1','1250.00','','14.0','Fer_Varao_SPP','Tab_Ferragens_11','ferragens','ML','','',''),(33,2,10,'','SUPORTE VARAO','2','','','0.0','Fer_Suporte Varao','Tab_Ferragens_11','ferragens','UND','','',''),(34,3,0,'mod inf lava louça','MODULO','','H1','L1','P1','','','','','','',''),(35,3,1,'','COSTA CHAPAR [0000]','1','HM','LM','10.0','Mat_Costas','Tab_Material_11','','M2','','',''),(36,3,2,'','LATERAL [2022]','2','HM','PM','19.0','Mat_Laterais','Tab_Material_11','','M2','','',''),(37,3,3,'','TETO [2000]','1','LM','PM','19.0','Mat_Tetos','Tab_Material_11','','M2','','',''),(38,3,4,'','FUNDO [2000] + PES_1','1','LM','PM','19.0','Mat_Fundos','Tab_Material_11','','M2','PES_1','',''),(39,3,5,'','PES_1','6','','','100.0','Fer_Pes_2','Tab_Ferragens_11','','UND','','',''),(40,3,6,'montagem modulo','MAO DE OBRA  -MIN-','20','','','','nan','nan','mao_obra','','','','');
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

-- Dump completed on 2025-07-03 11:15:52
