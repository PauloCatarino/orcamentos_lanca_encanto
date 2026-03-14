#!/usr/bin/env python
"""Quick migration: Add missing preco_atualizado_em column"""
from sqlalchemy import text
from Martelo_Orcamentos_V2.app.db import engine

print("Adding missing columns to orcamentos table...")

with engine.begin() as conn:
    try:
        # Add the timestamp column
        conn.execute(text("""
            ALTER TABLE orcamentos
            ADD COLUMN preco_atualizado_em DATETIME NULL 
            COMMENT 'Timestamp da última modificação do preço'
        """))
        print("✓ Added column: preco_atualizado_em")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("✓ Column preco_atualizado_em already exists")
        else:
            print(f"✗ Error: {e}")
            exit(1)
    
    try:
        # Create indices
        conn.execute(text("""
            CREATE INDEX idx_preco_atualizado_em ON orcamentos(preco_atualizado_em)
        """))
        print("✓ Created index: idx_preco_atualizado_em")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("✓ Index already exists")
        else:
            print(f"⚠ Index creation: {e}")
    
    try:
        # Update existing records
        conn.execute(text("""
            UPDATE orcamentos 
            SET preco_atualizado_em = IF(updated_at IS NOT NULL, updated_at, created_at)
            WHERE preco_atualizado_em IS NULL AND preco_total IS NOT NULL
        """))
        print("✓ Updated existing records with timestamp")
    except Exception as e:
        print(f"⚠ Update: {e}")

print("\n✓ Migration complete!")
