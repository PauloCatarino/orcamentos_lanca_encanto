-- =========================================================================
-- MIGRATION: Price Management System
-- Data: 2026-01-19
-- 
-- OBJETIVO: Adicionar suporte para rastrear edições manuais de preço
--           e sincronização entre diferentes interfaces
--
-- COMPATIBILIDADE: Seguro para dados existentes - usa ALTER TABLE
--                  Não quebra retro-compatibilidade
--
-- BACKUP: Recomendado fazer cópia da BD antes de executar
-- =========================================================================

-- 1. Adicionar coluna para rastrear se preço foi editado manualmente
--    Usa a coluna reservado1 existente, renomeando-a para melhor clareza
--    Se a coluna já foi usada para outro fim, este passo falhará
--    (nesse caso, usar uma coluna reservado diferente)
ALTER TABLE orcamentos 
MODIFY COLUMN reservado1 TINYINT(1) DEFAULT 0 COMMENT 'Flag: 1=preço manual, 0=preço calculado';

-- 2. Adicionar coluna para timestamp de última atualização do preço
--    Permite auditar quando foi a última vez que o preço foi modificado
ALTER TABLE orcamentos
ADD COLUMN preco_atualizado_em DATETIME NULL 
COMMENT 'Timestamp da última modificação do preço (manual ou automática)';

-- 3. Criar índices para melhorar performance nas queries
--    Útil para filtrar orçamentos com preço manual vs automático
CREATE INDEX idx_preco_total_manual ON orcamentos(reservado1);
CREATE INDEX idx_preco_atualizado_em ON orcamentos(preco_atualizado_em);

-- 4. Migrar dados existentes
--    Para orçamentos existentes:
--    - Se preco_total != NULL: marcar como "calculado" (reservado1 = 0)
--    - Definir preco_atualizado_em para updated_at (quando foi criado/modificado)
UPDATE orcamentos 
SET 
  reservado1 = 0,
  preco_atualizado_em = IF(updated_at IS NOT NULL, updated_at, created_at)
WHERE preco_total IS NOT NULL AND (reservado1 IS NULL OR reservado1 = '');

-- 5. Para orçamentos sem preco_total (se existirem):
--    - Deixar como "não calculado ainda" (reservado1 = 0)
UPDATE orcamentos 
SET 
  reservado1 = 0,
  preco_atualizado_em = NOW()
WHERE preco_total IS NULL AND (reservado1 IS NULL OR reservado1 = '');

-- =========================================================================
-- FIM DA MIGRATION
-- =========================================================================

-- ROLLBACK (em caso de necessidade):
/*
ALTER TABLE orcamentos 
MODIFY COLUMN reservado1 VARCHAR(255) DEFAULT NULL;

ALTER TABLE orcamentos
DROP COLUMN preco_atualizado_em;

DROP INDEX idx_preco_total_manual ON orcamentos;
DROP INDEX idx_preco_atualizado_em ON orcamentos;

UPDATE orcamentos SET reservado1 = NULL;
*/
