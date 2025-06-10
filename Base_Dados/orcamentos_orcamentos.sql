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
-- Table structure for table `orcamentos`
--

DROP TABLE IF EXISTS `orcamentos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orcamentos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `utilizador` text,
  `ano` varchar(4) DEFAULT NULL,
  `num_orcamento` varchar(20) DEFAULT NULL,
  `versao` varchar(10) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `nome_cliente` varchar(255) DEFAULT NULL,
  `enc_phc` varchar(50) DEFAULT NULL,
  `data` varchar(10) DEFAULT NULL,
  `preco` float DEFAULT NULL,
  `ref_cliente` varchar(50) DEFAULT NULL,
  `obra` text,
  `caracteristicas` text,
  `localizacao` text,
  `info_1` text,
  `info_2` text,
  PRIMARY KEY (`id`),
  KEY `id_cliente` (`id_cliente`),
  CONSTRAINT `orcamentos_ibfk_1` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orcamentos`
--

LOCK TABLES `orcamentos` WRITE;
/*!40000 ALTER TABLE `orcamentos` DISABLE KEYS */;
INSERT INTO `orcamentos` VALUES (2,1,'Andreia','2025','250001','00','Falta Orcamentar','JF_VIVA','','23/02/2025',630,'2502023','','','','1º orcamento criado com sucesso\n',''),(4,1,'Andreia','2025','250001','01','Falta Orcamentar','JF_VIVA','','23/02/2025',630,'2502023','','','','1 versao alterada\n',''),(5,1,'Paulo','2025','250001','02','Falta Orcamentar','JF_VIVA','','02/03/2025',1236,'2503001','','','','Roupeiros portas abrir\n',''),(6,2,'Andreia','2025','250002','00','Falta Orcamentar','Cicomol','','02/03/2025',0,'','','','','roupeiros &  cozinhas',''),(7,2,'Catia','2025','250002','01','Falta Orcamentar','Cicomol','','02/03/2025',125.6,'','','','','roupeiros &  cozinhas\nfalta preço',''),(9,2,'Paulo','2025','250003','00','Falta Orcamentar','Cicomol','','12/04/2025',1520,'','Quinta das palmeiras','Modulos roupeiros portas','Leiria','obra para concurso','nao perder tempo'),(10,2,'Paulo','2025','250003','01','Falta Orcamentar','Cicomol','','12/04/2025',0,'','Quinta das palmeiras','Modulos roupeiros portas -Esta obra tem de ser revista novamente ','Leiria','obra para concurso - com novos dados','nao perder tempo');
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

-- Dump completed on 2025-06-08 23:17:47
