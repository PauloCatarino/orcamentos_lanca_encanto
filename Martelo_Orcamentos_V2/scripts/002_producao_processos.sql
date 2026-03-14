-- Tabela de processos de producao (codigo AA.NNNN_VV_PP)
CREATE TABLE IF NOT EXISTS producao (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codigo_processo VARCHAR(32) NOT NULL,
    ano VARCHAR(4) NOT NULL,
    num_enc_phc VARCHAR(16) NOT NULL,
    versao_obra VARCHAR(2) NOT NULL DEFAULT '01',
    versao_plano VARCHAR(2) NOT NULL DEFAULT '01',

    orcamento_id BIGINT NULL,
    client_id BIGINT NULL,

    responsavel VARCHAR(100) NULL,
    estado VARCHAR(50) NULL,

    nome_cliente VARCHAR(255) NULL,
    nome_cliente_simplex VARCHAR(255) NULL,
    num_cliente_phc VARCHAR(64) NULL,
    ref_cliente VARCHAR(64) NULL,

    num_orcamento VARCHAR(16) NULL,
    versao_orc VARCHAR(2) NULL,

    obra VARCHAR(255) NULL,
    localizacao VARCHAR(255) NULL,
    descricao_orcamento TEXT NULL,

    data_entrega VARCHAR(10) NULL,
    data_inicio VARCHAR(10) NULL,
    preco_total DECIMAL(14,2) NULL,
    qt_artigos INT NULL,

    descricao_artigos TEXT NULL,
    materias_usados TEXT NULL,
    descricao_producao TEXT NULL,

    notas1 TEXT NULL,
    notas2 TEXT NULL,
    notas3 TEXT NULL,

    imagem_path VARCHAR(1024) NULL,
    pasta_servidor VARCHAR(1024) NULL,
    tipo_pasta VARCHAR(64) NULL,

    created_by BIGINT NULL,
    updated_by BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY u_producao_codigo (codigo_processo),
    UNIQUE KEY u_producao_chave (ano, num_enc_phc, versao_obra, versao_plano),
    KEY ix_producao_estado (estado),
    KEY ix_producao_cliente (nome_cliente),
    KEY ix_producao_data_entrega (data_entrega),
    KEY idx_orcamento (orcamento_id),
    KEY idx_cliente (client_id),
    CONSTRAINT fk_producao_orcamento FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE SET NULL,
    CONSTRAINT fk_producao_cliente FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PDF PRINT CONFIG
CREATE TABLE IF NOT EXISTS pdf_print_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(50) UNIQUE NOT NULL,
    default_quantity INT DEFAULT 1,
    default_paper_size VARCHAR(20) DEFAULT 'A4',
    default_orientation VARCHAR(20) DEFAULT 'vertical',
    default_double_sided BOOLEAN DEFAULT FALSE,
    default_color_mode VARCHAR(20) DEFAULT 'color',
    reservado1 VARCHAR(255),
    reservado2 VARCHAR(255),
    reservado3 VARCHAR(255),
    reservado4 VARCHAR(255),
    reservado5 VARCHAR(255),
    display_name VARCHAR(100),
    icon_path VARCHAR(512),
    priority INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pdf_config_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PDF PRINT JOB
CREATE TABLE IF NOT EXISTS pdf_print_job (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    producao_id BIGINT NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    md5_hash VARCHAR(32),
    category VARCHAR(50),
    priority INT DEFAULT 8,
    pdf_origin VARCHAR(50),
    quantity INT DEFAULT 1,
    paper_size VARCHAR(20) DEFAULT 'A4',
    orientation VARCHAR(20) DEFAULT 'vertical',
    page_range VARCHAR(50),
    double_sided BOOLEAN DEFAULT FALSE,
    color_mode VARCHAR(20) DEFAULT 'color',
    status VARCHAR(50) DEFAULT 'pending',
    print_datetime DATETIME,
    print_duration_ms INT,
    print_error_msg TEXT,
    reservado1 VARCHAR(255),
    reservado2 VARCHAR(255),
    reservado3 VARCHAR(255),
    reservado4 VARCHAR(255),
    reservado5 VARCHAR(255),
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pdf_job_producao (producao_id),
    INDEX idx_pdf_job_status (status),
    INDEX idx_pdf_job_category (category),
    INDEX idx_pdf_job_created_at (created_at),
    CONSTRAINT fk_pdf_job_producao FOREIGN KEY (producao_id) REFERENCES producao(id) ON DELETE CASCADE,
    CONSTRAINT fk_pdf_job_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PDF PRINT QUEUE
CREATE TABLE IF NOT EXISTS pdf_print_queue (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_id BIGINT,
    queue_position INT NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    priority INT,
    category VARCHAR(50),
    quantity INT DEFAULT 1,
    paper_size VARCHAR(20) DEFAULT 'A4',
    orientation VARCHAR(20) DEFAULT 'vertical',
    reservado1 VARCHAR(255),
    reservado2 VARCHAR(255),
    reservado3 VARCHAR(255),
    reservado4 VARCHAR(255),
    reservado5 VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pdf_queue_position (queue_position),
    INDEX idx_pdf_queue_job (job_id),
    CONSTRAINT fk_pdf_queue_job FOREIGN KEY (job_id) REFERENCES pdf_print_job(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
