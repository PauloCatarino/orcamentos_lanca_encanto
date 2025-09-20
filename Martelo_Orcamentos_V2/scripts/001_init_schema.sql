-- Ajuste o nome da base de dados em conformidade
CREATE DATABASE IF NOT EXISTS `orcamentos_v2`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE `orcamentos_v2`;

-- Limpeza para ambiente de testes (DROP com ordem segura)
DROP TABLE IF EXISTS dados_items_acabamentos;
DROP TABLE IF EXISTS dados_items_sistemas_correr;
DROP TABLE IF EXISTS dados_items_ferragens;
DROP TABLE IF EXISTS dados_items_materiais;
DROP TABLE IF EXISTS dados_def_pecas;
DROP TABLE IF EXISTS dados_modulo_medidas;
DROP TABLE IF EXISTS orcamento_items;
DROP TABLE IF EXISTS orcamentos;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS app_settings;

-- Tabela de utilizadores
CREATE TABLE IF NOT EXISTS users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(255) UNIQUE,
  pass_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- App settings (key/value)
CREATE TABLE IF NOT EXISTS app_settings (
  `key` VARCHAR(64) PRIMARY KEY,
  `value` LONGTEXT
) ENGINE=InnoDB;

-- Clients
CREATE TABLE IF NOT EXISTS clients (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  nome_simplex VARCHAR(255),
  morada TEXT,
  email VARCHAR(255),
  web_page VARCHAR(255),
  telefone VARCHAR(64),
  telemovel VARCHAR(64),
  num_cliente_phc VARCHAR(64),
  info_1 LONGTEXT,
  info_2 LONGTEXT,
  notas LONGTEXT,
  extras JSON,
  reservado1 VARCHAR(255),
  reservado2 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_clients_nome (nome),
  INDEX ix_clients_nome_simplex (nome_simplex)
) ENGINE=InnoDB;

-- Orçamentos
CREATE TABLE IF NOT EXISTS orcamentos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao CHAR(2) NOT NULL DEFAULT '00',
  client_id BIGINT NOT NULL,
  status VARCHAR(32),
  data VARCHAR(10),
  preco_total DECIMAL(14,2),
  ref_cliente VARCHAR(64),
  enc_phc VARCHAR(64),
  obra VARCHAR(255),
  descricao_orcamento LONGTEXT,
  localizacao VARCHAR(255),
  info_1 LONGTEXT,
  info_2 LONGTEXT,
  notas LONGTEXT,
  extras JSON,
  reservado1 VARCHAR(255),
  reservado2 VARCHAR(255),
  created_by BIGINT NULL,
  updated_by BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY u_orc_ano_num_ver (ano, num_orcamento, versao),
  CONSTRAINT fk_orc_cliente FOREIGN KEY (client_id) REFERENCES clients(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Itens do orçamento
CREATE TABLE IF NOT EXISTS orcamento_items (
  id_item BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_orcamento BIGINT NOT NULL,
  item_ord INT NOT NULL DEFAULT 1,
  codigo VARCHAR(64),
  descricao LONGTEXT,
  altura DECIMAL(10,2) DEFAULT 0,
  largura DECIMAL(10,2) DEFAULT 0,
  profundidade DECIMAL(10,2) DEFAULT 0,
  und VARCHAR(16) DEFAULT 'und',
  qt DECIMAL(10,2) DEFAULT 1,
  preco_unitario DECIMAL(14,2) DEFAULT 0,
  preco_total DECIMAL(14,2) DEFAULT 0,
  custo_produzido DECIMAL(14,2) DEFAULT 0,
  custo_total_orlas DECIMAL(14,2) DEFAULT 0,
  custo_total_mao_obra DECIMAL(14,2) DEFAULT 0,
  custo_total_materia_prima DECIMAL(14,2) DEFAULT 0,
  custo_total_acabamentos DECIMAL(14,2) DEFAULT 0,
  margem_lucro_perc DECIMAL(6,4) DEFAULT 0,
  valor_margem DECIMAL(14,2) DEFAULT 0,
  custos_admin_perc DECIMAL(6,4) DEFAULT 0,
  valor_custos_admin DECIMAL(14,2) DEFAULT 0,
  margem_acabamentos_perc DECIMAL(6,4) DEFAULT 0,
  valor_acabamentos DECIMAL(14,2) DEFAULT 0,
  margem_mp_orlas_perc DECIMAL(6,4) DEFAULT 0,
  valor_mp_orlas DECIMAL(14,2) DEFAULT 0,
  margem_mao_obra_perc DECIMAL(6,4) DEFAULT 0,
  valor_mao_obra DECIMAL(14,2) DEFAULT 0,
  notas LONGTEXT,
  extras JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_item_ord (id_orcamento, item_ord),
  CONSTRAINT fk_item_orc FOREIGN KEY (id_orcamento) REFERENCES orcamentos(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Tabela genérica de medidas do módulo (FK id_item_fk)
CREATE TABLE IF NOT EXISTS dados_modulo_medidas (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  H DECIMAL(10,2) DEFAULT 0, L DECIMAL(10,2) DEFAULT 0, P DECIMAL(10,2) DEFAULT 0,
  H1 DECIMAL(10,2) DEFAULT 0, L1 DECIMAL(10,2) DEFAULT 0, P1 DECIMAL(10,2) DEFAULT 0,
  H2 DECIMAL(10,2) DEFAULT 0, L2 DECIMAL(10,2) DEFAULT 0, P2 DECIMAL(10,2) DEFAULT 0,
  H3 DECIMAL(10,2) DEFAULT 0, L3 DECIMAL(10,2) DEFAULT 0, P3 DECIMAL(10,2) DEFAULT 0,
  H4 DECIMAL(10,2) DEFAULT 0, L4 DECIMAL(10,2) DEFAULT 0, P4 DECIMAL(10,2) DEFAULT 0,
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_medidas_item (id_item_fk)
) ENGINE=InnoDB;

-- Definição de peças
CREATE TABLE IF NOT EXISTS dados_def_pecas (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  descricao_livre LONGTEXT, def_peca VARCHAR(255), descricao LONGTEXT,
  qt_mod VARCHAR(64), qt_und DECIMAL(10,2),
  comp VARCHAR(255), larg VARCHAR(255), esp VARCHAR(255),
  mps TINYINT, mo TINYINT, orla TINYINT, blk TINYINT,
  mat_default VARCHAR(100), tab_default VARCHAR(100),
  ref_le VARCHAR(100), descricao_no_orcamento LONGTEXT,
  ptab DECIMAL(12,2), pliq DECIMAL(12,2), des1plus DECIMAL(6,2), des1minus DECIMAL(6,2),
  und VARCHAR(20), desp DECIMAL(6,4),
  corres_orla_0_4 VARCHAR(50), corres_orla_1_0 VARCHAR(50),
  tipo VARCHAR(50), familia VARCHAR(50),
  comp_mp DECIMAL(10,2), larg_mp DECIMAL(10,2), esp_mp DECIMAL(10,2), mp TINYINT,
  orla_c1 DECIMAL(10,2), orla_c2 DECIMAL(10,2), orla_l1 DECIMAL(10,2), orla_l2 DECIMAL(10,2),
  ml_c1 DECIMAL(12,2), ml_c2 DECIMAL(12,2), ml_l1 DECIMAL(12,2), ml_l2 DECIMAL(12,2),
  custo_ml_c1 DECIMAL(12,2), custo_ml_c2 DECIMAL(12,2), custo_ml_l1 DECIMAL(12,2), custo_ml_l2 DECIMAL(12,2),
  qt_total DECIMAL(12,2), comp_res DECIMAL(10,2), larg_res DECIMAL(10,2), esp_res DECIMAL(10,2),
  area_m2_und DECIMAL(12,4), spp_ml_und DECIMAL(12,4),
  cp09_custo_mp DECIMAL(12,2), custo_mp_und DECIMAL(12,2), custo_mp_total DECIMAL(12,2),
  soma_custo_und DECIMAL(12,2), soma_custo_total DECIMAL(12,2), soma_custo_acb DECIMAL(12,2),
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_def_item (id_item_fk)
) ENGINE=InnoDB;

-- Tabelas de itens associados (materiais/ferragens/sistemas/acabamentos)
CREATE TABLE IF NOT EXISTS dados_items_materiais (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  linha INT DEFAULT 1,
  material VARCHAR(255), descricao LONGTEXT, und VARCHAR(20), pliq DECIMAL(12,2), desp DECIMAL(6,4),
  comp_mp DECIMAL(10,2), larg_mp DECIMAL(10,2), esp_mp DECIMAL(10,2),
  custo_mp_und DECIMAL(12,2), custo_mp_total DECIMAL(12,2),
  nao_stock TINYINT DEFAULT 0,
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_mat_item (id_item_fk)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dados_items_ferragens (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  linha INT DEFAULT 1,
  material VARCHAR(255), descricao LONGTEXT, und VARCHAR(20), pliq DECIMAL(12,2), desp DECIMAL(6,4),
  spp_ml_und DECIMAL(12,4), custo_mp_und DECIMAL(12,2), custo_mp_total DECIMAL(12,2),
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_fer_item (id_item_fk)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dados_items_sistemas_correr (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  linha INT DEFAULT 1,
  material VARCHAR(255), descricao LONGTEXT, und VARCHAR(20), pliq DECIMAL(12,2), desp DECIMAL(6,4),
  custo_mp_und DECIMAL(12,2), custo_mp_total DECIMAL(12,2),
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_sc_item (id_item_fk)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dados_items_acabamentos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_item_fk BIGINT NOT NULL,
  linha INT DEFAULT 1,
  material VARCHAR(255), descricao LONGTEXT, und VARCHAR(20), pliq DECIMAL(12,2), desp DECIMAL(6,4),
  custo_acb_und DECIMAL(12,2), custo_acb_total DECIMAL(12,2),
  notas LONGTEXT, extras JSON,
  reservado1 VARCHAR(255), reservado2 VARCHAR(255), reservado3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_acb_item (id_item_fk)
) ENGINE=InnoDB;
