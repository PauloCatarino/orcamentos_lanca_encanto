#!/usr/bin/env python
from sqlalchemy import text
from Martelo_Orcamentos_V2.app.db import engine

with engine.connect() as conn:
    result = conn.execute(text('DESCRIBE orcamentos')).fetchall()
    columns = [row[0] for row in result]
    
    print('Checking migration status:')
    has_manual = 'reservado1' in columns
    has_timestamp = 'preco_atualizado_em' in columns
    print(f'  reservado1: {"OK" if has_manual else "MISSING"}')
    print(f'  preco_atualizado_em: {"OK" if has_timestamp else "MISSING"}')
    
    if has_manual and has_timestamp:
        print('\n✓ Migration SUCCESS!')
        exit(0)
    else:
        print('\n✗ Migration INCOMPLETE')
        exit(1)
