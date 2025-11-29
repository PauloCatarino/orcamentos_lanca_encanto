-- Ajuste o nome da base de dados em conformidade
CREATE DATABASE IF NOT EXISTS `orcamentos_v2`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE `orcamentos_v2`;

-- ===========================
-- Limpeza SEGURA (ambiente de testes)
-- ===========================
SET FOREIGN_KEY_CHECKS = 0;

-- 1) Tabelas que dependem de users/clients/orcamentos/etc.
DROP TABLE IF EXISTS materia_prima_preferences;
DROP TABLE IF EXISTS dados_items_acabamentos;
DROP TABLE IF EXISTS dados_items_sistemas_correr;
DROP TABLE IF EXISTS dados_items_ferragens;
DROP TABLE IF EXISTS dados_items_modelo_items;\r\nDROP TABLE IF EXISTS dados_items_modelos;\r\nDROP TABLE IF EXISTS dados_items_materiais;
DROP TABLE IF EXISTS dados_def_pecas;
DROP TABLE IF EXISTS dados_modulo_medidas;
DROP TABLE IF EXISTS custeio_modulo_linhas;
DROP TABLE IF EXISTS custeio_modulos;
DROP TABLE IF EXISTS custeio_desp_backup;

-- 2) Itens e orçamentos (filhas antes do pai)
DROP TABLE IF EXISTS orcamento_items;
DROP TABLE IF EXISTS orcamentos;

-- 3) Pais
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS users;

-- 4) Outras
DROP TABLE IF EXISTS app_settings;

SET FOREIGN_KEY_CHECKS = 1;

-- ===========================
-- Criação de Tabelas (ordem correta)
-- ===========================

-- USERS
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

-- APP SETTINGS
CREATE TABLE IF NOT EXISTS app_settings (
  `key`   VARCHAR(64) PRIMARY KEY,
  `value` LONGTEXT
) ENGINE=InnoDB;

-- CLIENTS
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

-- ORCAMENTOS
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
  CONSTRAINT fk_orc_cliente FOREIGN KEY (client_id)
    REFERENCES clients(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ORCAMENTO ITEMS
CREATE TABLE IF NOT EXISTS orcamento_items (
  id_item BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_orcamento BIGINT NOT NULL,
  versao CHAR(2) NOT NULL DEFAULT '01',
  item_ord INT NOT NULL DEFAULT 1,
  item VARCHAR(255),
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
  ajuste DECIMAL(14,2) DEFAULT 0,
  custo_total_orlas DECIMAL(14,2) DEFAULT 0,
  custo_total_mao_obra DECIMAL(14,2) DEFAULT 0,
  custo_total_materia_prima DECIMAL(14,2) DEFAULT 0,
  custo_total_acabamentos DECIMAL(14,2) DEFAULT 0,
  margem_lucro_perc DECIMAL(6,2) DEFAULT 0,
  valor_margem DECIMAL(14,2) DEFAULT 0,
  custos_admin_perc DECIMAL(6,2) DEFAULT 0,
  valor_custos_admin DECIMAL(14,2) DEFAULT 0,
  margem_acabamentos_perc DECIMAL(6,2) DEFAULT 0,
  valor_acabamentos DECIMAL(14,2) DEFAULT 0,
  margem_mp_orlas_perc DECIMAL(6,2) DEFAULT 0,
  valor_mp_orlas DECIMAL(14,2) DEFAULT 0,
  margem_mao_obra_perc DECIMAL(6,2) DEFAULT 0,
  valor_mao_obra DECIMAL(14,2) DEFAULT 0,
  notas LONGTEXT,
  extras JSON,
  custo_colagem DECIMAL(14,2) DEFAULT 0,
  reservado_2 VARCHAR(255),
  reservado_3 VARCHAR(255),
  created_by BIGINT NULL,
  updated_by BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_item_ord (id_orcamento, item_ord),
  CONSTRAINT fk_item_orc FOREIGN KEY (id_orcamento)
    REFERENCES orcamentos(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- MEDIDAS DO MÓDULO
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

-- MODULOS DE CUSTEIO
CREATE TABLE IF NOT EXISTS custeio_modulos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  descricao LONGTEXT,
  imagem_path VARCHAR(1024),
  is_global TINYINT(1) NOT NULL DEFAULT 0,
  user_id BIGINT NULL,
  extras JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_modulos_user (user_id),
  CONSTRAINT fk_modulos_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS custeio_modulo_linhas (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  modulo_id BIGINT NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  dados JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_modulo_linhas_mod (modulo_id),
  CONSTRAINT fk_modulo_linhas_mod FOREIGN KEY (modulo_id) REFERENCES custeio_modulos(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;
-- DEF PEÇAS
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

-- ITENS: MATERIAIS / FERRAGENS / SISTEMAS / ACABAMENTOS
CREATE TABLE IF NOT EXISTS dados_items_materiais (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id BIGINT NOT NULL,
  orcamento_id BIGINT NOT NULL,
  cliente_id BIGINT NOT NULL,
  user_id BIGINT NULL,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao VARCHAR(4) NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  grupo_material VARCHAR(64),
  descricao VARCHAR(255),
  ref_le VARCHAR(64),
  descricao_material VARCHAR(255),
  preco_tab DECIMAL(12,4),
  preco_liq DECIMAL(12,4),
  margem DECIMAL(8,6),
  desconto DECIMAL(8,6),
  und VARCHAR(12),
  desp DECIMAL(8,6),
  orl_0_4 VARCHAR(64),
  orl_1_0 VARCHAR(64),
  tipo VARCHAR(64),
  familia VARCHAR(64),
  comp_mp INT,
  larg_mp INT,
  esp_mp INT,
  id_mp VARCHAR(64),
  nao_stock TINYINT DEFAULT 0,
  linha INT DEFAULT 1,
  custo_mp_und DECIMAL(12,4),
  custo_mp_total DECIMAL(12,4),
  reserva_1 VARCHAR(255),
  reserva_2 VARCHAR(255),
  reserva_3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_items_mat_item (item_id),
  INDEX ix_items_mat_orc (orcamento_id),
  INDEX ix_items_mat_ref (ref_le),
  CONSTRAINT fk_items_mat_item FOREIGN KEY (item_id) REFERENCES orcamento_items(id_item) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_mat_orc FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_mat_cliente FOREIGN KEY (cliente_id) REFERENCES clients(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_mat_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS dados_items_ferragens (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id BIGINT NOT NULL,
  orcamento_id BIGINT NOT NULL,
  cliente_id BIGINT NOT NULL,
  user_id BIGINT NULL,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao VARCHAR(4) NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  grupo_ferragem VARCHAR(64),
  descricao VARCHAR(255),
  ref_le VARCHAR(64),
  descricao_material VARCHAR(255),
  preco_tab DECIMAL(12,4),
  preco_liq DECIMAL(12,4),
  margem DECIMAL(8,6),
  desconto DECIMAL(8,6),
  und VARCHAR(12),
  desp DECIMAL(8,6),
  tipo VARCHAR(64),
  familia VARCHAR(64),
  comp_mp INT,
  larg_mp INT,
  esp_mp INT,
  id_mp VARCHAR(64),
  nao_stock TINYINT DEFAULT 0,
  linha INT DEFAULT 1,
  spp_ml_und DECIMAL(12,4),
  custo_mp_und DECIMAL(12,4),
  custo_mp_total DECIMAL(12,4),
  reserva_1 VARCHAR(255),
  reserva_2 VARCHAR(255),
  reserva_3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_items_fer_item (item_id),
  INDEX ix_items_fer_orc (orcamento_id),
  INDEX ix_items_fer_ref (ref_le),
  CONSTRAINT fk_items_fer_item FOREIGN KEY (item_id) REFERENCES orcamento_items(id_item) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_fer_orc FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_fer_cliente FOREIGN KEY (cliente_id) REFERENCES clients(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_fer_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS dados_items_sistemas_correr (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id BIGINT NOT NULL,
  orcamento_id BIGINT NOT NULL,
  cliente_id BIGINT NOT NULL,
  user_id BIGINT NULL,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao VARCHAR(4) NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  grupo_sistema VARCHAR(64),
  descricao VARCHAR(255),
  ref_le VARCHAR(64),
  descricao_material VARCHAR(255),
  preco_tab DECIMAL(12,4),
  preco_liq DECIMAL(12,4),
  margem DECIMAL(8,6),
  desconto DECIMAL(8,6),
  und VARCHAR(12),
  desp DECIMAL(8,6),
  tipo VARCHAR(64),
  familia VARCHAR(64),
  comp_mp INT,
  larg_mp INT,
  esp_mp INT,
  orl_0_4 VARCHAR(64),
  orl_1_0 VARCHAR(64),
  id_mp VARCHAR(64),
  nao_stock TINYINT DEFAULT 0,
  linha INT DEFAULT 1,
  custo_mp_und DECIMAL(12,4),
  custo_mp_total DECIMAL(12,4),
  reserva_1 VARCHAR(255),
  reserva_2 VARCHAR(255),
  reserva_3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_items_sis_item (item_id),
  INDEX ix_items_sis_orc (orcamento_id),
  INDEX ix_items_sis_ref (ref_le),
  CONSTRAINT fk_items_sis_item FOREIGN KEY (item_id) REFERENCES orcamento_items(id_item) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_sis_orc FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_sis_cliente FOREIGN KEY (cliente_id) REFERENCES clients(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_sis_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS dados_items_acabamentos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  item_id BIGINT NOT NULL,
  orcamento_id BIGINT NOT NULL,
  cliente_id BIGINT NOT NULL,
  user_id BIGINT NULL,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao VARCHAR(4) NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  grupo_acabamento VARCHAR(64),
  descricao VARCHAR(255),
  ref_le VARCHAR(64),
  descricao_material VARCHAR(255),
  preco_tab DECIMAL(12,4),
  preco_liq DECIMAL(12,4),
  margem DECIMAL(8,6),
  desconto DECIMAL(8,6),
  und VARCHAR(12),
  desp DECIMAL(8,6),
  tipo VARCHAR(64),
  familia VARCHAR(64),
  comp_mp INT,
  larg_mp INT,
  esp_mp INT,
  id_mp VARCHAR(64),
  nao_stock TINYINT DEFAULT 0,
  linha INT DEFAULT 1,
  custo_acb_und DECIMAL(12,4),
  custo_acb_total DECIMAL(12,4),
  reserva_1 VARCHAR(255),
  reserva_2 VARCHAR(255),
  reserva_3 VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_items_acb_item (item_id),
  INDEX ix_items_acb_orc (orcamento_id),
  INDEX ix_items_acb_ref (ref_le),
  CONSTRAINT fk_items_acb_item FOREIGN KEY (item_id) REFERENCES orcamento_items(id_item) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_acb_orc FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_acb_cliente FOREIGN KEY (cliente_id) REFERENCES clients(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_items_acb_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;


CREATE TABLE IF NOT EXISTS dados_items_modelos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  orcamento_id BIGINT NOT NULL,
  item_id BIGINT NULL,
  user_id BIGINT NULL,
  nome_modelo VARCHAR(128) NOT NULL,
  tipo_menu VARCHAR(32) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_di_model_orc FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_di_model_item FOREIGN KEY (item_id) REFERENCES orcamento_items(id_item) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_di_model_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS custeio_producao_config (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  orcamento_id BIGINT NOT NULL,
  cliente_id BIGINT NULL,
  user_id BIGINT NULL,
  ano VARCHAR(4) NOT NULL,
  num_orcamento VARCHAR(16) NOT NULL,
  versao VARCHAR(4) NOT NULL,
  modo VARCHAR(8) NOT NULL DEFAULT 'STD',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT u_custeio_producao_config_ctx UNIQUE (orcamento_id, versao, user_id),
  CONSTRAINT fk_cpc_orcamento FOREIGN KEY (orcamento_id)
    REFERENCES orcamentos(id) ON DELETE CASCADE,
  CONSTRAINT fk_cpc_cliente FOREIGN KEY (cliente_id)
    REFERENCES clients(id) ON DELETE SET NULL,
  CONSTRAINT fk_cpc_user FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS custeio_producao_valores (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  config_id BIGINT NOT NULL,
  descricao_equipamento VARCHAR(128) NOT NULL,
  abreviatura VARCHAR(16) NOT NULL,
  valor_std DECIMAL(18,4) NOT NULL DEFAULT 0,
  valor_serie DECIMAL(18,4) NOT NULL DEFAULT 0,
  resumo VARCHAR(255) NULL,
  ordem INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_cpp_config FOREIGN KEY (config_id)
    REFERENCES custeio_producao_config(id) ON DELETE CASCADE,
  CONSTRAINT u_custeio_producao_valor_desc UNIQUE (config_id, descricao_equipamento)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dados_items_modelo_items (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  modelo_id BIGINT NOT NULL,
  tipo_menu VARCHAR(32) NOT NULL,
  ordem INT NOT NULL DEFAULT 0,
  dados LONGTEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_di_model_item_parent FOREIGN KEY (modelo_id)
    REFERENCES dados_items_modelos(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Preferências de colunas da página Matérias-Primas (por utilizador)
CREATE TABLE IF NOT EXISTS materia_prima_preferences (
  user_id BIGINT NOT NULL PRIMARY KEY,
  columns TEXT NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_mpp_user FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Backup de desperdicio quando ativa a opcao Nao Stock no resumo de placas
CREATE TABLE IF NOT EXISTS custeio_desp_backup (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  orcamento_id BIGINT NOT NULL,
  versao VARCHAR(4) NOT NULL,
  user_id BIGINT NULL,
  custeio_item_id BIGINT NOT NULL,
  desp_original DECIMAL(18,4) NOT NULL DEFAULT 0,
  blk_original TINYINT(1) NOT NULL DEFAULT 0,
  nao_stock_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY u_custeio_desp_backup_item (custeio_item_id),
  INDEX ix_custeio_desp_backup_ctx (orcamento_id, versao, custeio_item_id)
) ENGINE=InnoDB;

