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