# Titulo

## Su- Titulo


Esse é o meu primeiro README
*italico*

**negrito**
- Elemento 1
- Elemento 2

1) Elemento 1
2) Elemento 2

[Link para o Google] (https://www.google.com)

[Link do Video] (https://youtu.be/-M4pMd2yQOM)

![Link da imagem](https://th.bing.com/th?id=OSK.1bd96804749cb2cd25815989f67a03c6&w=188&h=132&c=7&o=6&pid=SANGAM)
## Resumo de Consumos

Foram adicionados módulos iniciais para o desenvolvimento do dashboard de consumos do orçamento.

- `db.py` faz a ligação à base MySQL com SQLAlchemy e fornece uma função para ler tabelas em `pandas`.
- `calculadora_consumos.py` inclui utilitários e o esqueleto de funções que irão calcular o consumo de materiais.
- `ui_loader.py` demonstra como carregar um ficheiro `.ui` criado no QtDesigner.

Recomenda‑se a criação de um ambiente virtual e instalação das dependências:

```bash
python3 -m venv venv
source venv/bin/activate
pip install sqlalchemy pymysql pandas openpyxl xlsxwriter matplotlib PySide6
```