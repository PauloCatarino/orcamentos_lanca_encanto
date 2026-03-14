-- Renomeia tabela antiga producao_processos para producao (simplificacao de nome)
-- Apenas executa se a tabela antiga existir e a nova nao existir.
SET @old_exists := (
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = 'producao_processos'
);
SET @new_exists := (
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = 'producao'
);

-- Se a antiga existe e a nova nao, faz rename
SET @do_rename := (SELECT @old_exists = 1 AND @new_exists = 0);
SELECT @do_rename AS will_rename;

-- Usa prepared statement para evitar erro se ja existir
SET @sql := CASE
    WHEN @do_rename THEN 'RENAME TABLE producao_processos TO producao'
    ELSE NULL
END;
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
