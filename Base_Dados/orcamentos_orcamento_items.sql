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
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orcamento_items`
--

LOCK TABLES `orcamento_items` WRITE;
/*!40000 ALTER TABLE `orcamento_items` DISABLE KEYS */;
INSERT INTO `orcamento_items` VALUES (1,1,'1','RP_01','ROUPEIRO 4 PORTAS ABRIR\n	- Interiores AGL_MLM_LINHO_CANCUN_10/16/19mm\n	- Bloco 3 Gavetas\n	- Corrediças EMUCA SILVER Extração Total com Amortecedor\n	- Puxador TIC_TAC',2500,2000,600,'und',1,201.6125,201.6125,161.29000000000002,4.01,72.68,84.6,0,0.15,24.193500000000004,0.05,8.0645,0.03,4.8387,0.02,3.2258000000000004),(2,3,'1','COZINHA','cozinha mod inf + mod sup\n	- Portas Abrir\n	- Bloco 3 Gavetas\n	- Rodape PVC/aluminio H100 branco',2500,2500,600,'und',1,764.4375,764.4375,611.5500000000001,5.68,419.47,186.4,0,0.15,91.7325,0.05,30.577500000000004,0.03,18.346500000000002,0.02,12.231000000000002),(3,3,'2','RP_02','roupeiro 4 portas\n	- Portas Abrir\n	- Bloco 3 Gavetas\n	- Rodape PVC/aluminio H100 branco',2500,2000,600,'und',1,604.975,604.975,483.97999999999996,5.32,339.4,139.26,0,0.15,72.597,0.05,24.198999999999998,0.03,14.519399999999997,0.02,9.679599999999999),(5,5,'1','RP_01','ROUPEIRO 4 PORTAS ABRIR\n	- Interiores AGL_MLM_LINHO_CANCUN_10/16/19mm\n	- Bloco 3 Gavetas\n	- Corrediças EMUCA SILVER Extração Total com Amortecedor\n	- Puxador TIC_TAC',2500,2000,600,'und',1,0,0,0,0,0,0,0,0.15,0,0.05,0,0.03,0,0.02,0);
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

-- Dump completed on 2025-07-03 11:16:22
