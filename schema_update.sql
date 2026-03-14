-- Convert nao_stock columns to INTEGER type and update values
ALTER TABLE dados_gerais_materiais MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_gerais_materiais SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_gerais_ferragens MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_gerais_ferragens SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_gerais_sistemas_correr MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_gerais_sistemas_correr SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_gerais_acabamentos MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_gerais_acabamentos SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_items_materiais MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_items_materiais SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_items_ferragens MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_items_ferragens SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_items_sistemas_correr MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_items_sistemas_correr SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

ALTER TABLE dados_items_acabamentos MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0;
UPDATE dados_items_acabamentos SET nao_stock = CASE WHEN nao_stock THEN 1 ELSE 0 END;

-- Base table for process cost definitions used in custeio
CREATE TABLE IF NOT EXISTS definicoes_pecas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo_peca_principal VARCHAR(64) NOT NULL,
    subgrupo_peca VARCHAR(128) NULL,
    nome_da_peca VARCHAR(255) NOT NULL UNIQUE,
    cp01_sec DECIMAL(12,4) NULL,
    cp02_orl DECIMAL(12,4) NULL,
    cp03_cnc DECIMAL(12,4) NULL,
    cp04_abd DECIMAL(12,4) NULL,
    cp05_prensa DECIMAL(12,4) NULL,
    cp06_esquad DECIMAL(12,4) NULL,
    cp07_embalagem DECIMAL(12,4) NULL,
    cp08_mao_de_obra DECIMAL(12,4) NULL,
    UNIQUE KEY u_definicoes_pecas_nome (nome_da_peca)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Adicionar coluna CP09_COLAGEM_und à tabela custeio_items (compatibilidade com builds antigos)
ALTER TABLE custeio_items
    ADD COLUMN IF NOT EXISTS cp09_colagem_und DECIMAL(18,4) NULL AFTER cp08_mao_de_obra_und;

-- Guardar miniatura associada à divisão independente no custeio
ALTER TABLE custeio_items
    ADD COLUMN IF NOT EXISTS icon_hint VARCHAR(512) NULL AFTER descricao;

-- Guardar o estado inicial do BLK no backup de desperdicio (Nao Stock)
ALTER TABLE custeio_desp_backup
    ADD COLUMN IF NOT EXISTS blk_original TINYINT(1) NOT NULL DEFAULT 0 AFTER desp_original;

-- Renomear coluna reservado_1 para custo_colagem na tabela orcamento_items
ALTER TABLE orcamento_items
    CHANGE COLUMN reservado_1 custo_colagem DECIMAL(14,2) NOT NULL DEFAULT 0;


-- Ajustar precisões das colunas percentuais e de custo na tabela orcamento_items
ALTER TABLE orcamento_items
    MODIFY COLUMN margem_lucro_perc DECIMAL(6,2) DEFAULT 0,
    MODIFY COLUMN custos_admin_perc DECIMAL(6,2) DEFAULT 0,
    MODIFY COLUMN margem_acabamentos_perc DECIMAL(6,2) DEFAULT 0,
    MODIFY COLUMN margem_mp_orlas_perc DECIMAL(6,2) DEFAULT 0,
    MODIFY COLUMN margem_mao_obra_perc DECIMAL(6,2) DEFAULT 0,
    MODIFY COLUMN custo_colagem DECIMAL(14,2) DEFAULT 0;

-- Tabela de clientes temporarios (clientes ainda nao existentes no PHC)
CREATE TABLE IF NOT EXISTS clientes_temporarios (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    nome_simplex VARCHAR(255) NULL,
    morada TEXT NULL,
    email VARCHAR(255) NULL,
    web_page VARCHAR(255) NULL,
    telefone VARCHAR(64) NULL,
    telemovel VARCHAR(64) NULL,
    num_cliente_phc VARCHAR(64) NULL,
    info_1 TEXT NULL,
    info_2 TEXT NULL,
    notas TEXT NULL,
    extras JSON NULL,
    reservado1 VARCHAR(255) NULL,
    reservado2 VARCHAR(255) NULL,
    reservado3 VARCHAR(255) NULL,
    reservado4 VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_clientes_temporarios_nome (nome),
    INDEX ix_clientes_temporarios_simplex (nome_simplex),
    INDEX ix_clientes_temporarios_num_phc (num_cliente_phc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

