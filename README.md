# Martelo — Orçamentos de Mobiliário (Martelo_Orcamentos_V2)

Uma aplicação para criar e gerir orçamentos de móveis, com cálculo detalhado de consumos, custos de produção e geração de relatórios. O projeto combina uma interface gráfica em PySide6 com lógica de cálculo (serviços), persistência via SQLAlchemy e utilitários para relatórios e exportação.

## Visão geral

- Interface: PySide6 (Qt) — janelas para gerir orçamentos, itens, materiais e configurações.
- Persistência: SQLAlchemy com MySQL (configurável via `settings.DB_URI`).
- Serviços: módulos em `Martelo_Orcamentos_V2/app/services` implementam a lógica de cálculo (CP, orlas, consumos, etc.).
- Export / Relatórios: scripts e utilitários para criar relatórios e gerar ficheiros (Excel/PDF).

## Funcionalidades principais

- Criar/editar orçamentos e itens.
- Calcular custos por componente (CPxx), mão-de-obra, CNC, embalagens, colagens e somas totais com base em definições de peças.
- Inferência automática de materiais/ferragens a partir da definição da peça (com regras e exceções).
- Modo de desenvolvimento com recarregamento e logging detalhado.

## Estrutura relevante

- `Martelo_Orcamentos_V2/ui` — interfaces (views, dialogs, modelos de tabela).
- `Martelo_Orcamentos_V2/app/services` — lógica do domínio (cálculos, regras, mapeamentos).
- `Martelo_Orcamentos_V2/app/models` — definições ORM (SQLAlchemy) para as tabelas da BD.
- `tests/` — testes e scripts de verificação (alguns podem ser utilitários internos).

## Requisitos e ambiente

Recomenda-se Python 3.11+ (o projeto foi testado com 3.13 em ambiente local). Use um ambiente virtual:

```powershell
python -m venv .venv_Martelo
.\.venv_Martelo\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se não existir `requirements.txt`, instale as dependências principais manualmente:

```powershell
pip install sqlalchemy pymysql pandas openpyxl xlsxwriter matplotlib PySide6 python-dotenv
```

## Configuração

- Copie `.env.example` (se existir) para `.env` e preencha as variáveis necessárias (por exemplo `DB_URI`, `SMTP_*`).
- As credenciais e a URI da base de dados estão em `Martelo_Orcamentos_V2/app/config.py` (ou via variável de ambiente `DB_URI`).

## Executar em modo desenvolvimento

Usar o script `run_dev.py` para arrancar a aplicação em modo de desenvolvimento (logging activo):

```powershell
python -m Martelo_Orcamentos_V2.run_dev
```

Isto activa logging para consola e ficheiro `martelo_debug.log` e abre a janela principal após login.

## Testes

- Os testes unitários estão em `tests/`. Há fixtures (em `tests/conftest.py`) que criam uma BD SQLite em memória para isolar os testes.
- Para executar um teste individual (exemplo):

```powershell
.\.venv_Martelo\Scripts\python.exe -m tests.test_divisao_independente_protection
```

## Desenvolvimento e contribuições

- Código: siga o estilo existente e prefira mudanças pequenas e focadas.
- Para novas funcionalidades, adicione testes que validem a lógica de cálculo e os casos de borda.
- Workflow sugerido:

```bash
git checkout -b feat/minha-melhoria
# fazer alterações
git add .
git commit -m "feat: descrição curta"
git push --set-upstream origin feat/minha-melhoria
```

## Logs e depuração

- O ficheiro de logs `martelo_debug.log` é criado no diretório do script/executável quando a aplicação é iniciada com `run_dev.py`.
- Defina níveis de logging no `run_dev._setup_logging()` se precisar de mais ou menos verbosidade.

## Notas de segurança e operações

- Tenha cuidado com `DB_URI` em ficheiros de configuração — prefira variáveis de ambiente para credenciais.
- O `run_dev.py` contém helpers para maskar a password na URI antes de escrever em logs.

## Contacto / Ajuda

Se precisares de ajuda, abre uma issue no repositório com uma descrição do problema, passos para reproduzir e (se aplicável) um ficheiro de exemplo.

---
_README atualizado para descrever o projecto Martelo Orçamentos de Mobiliário e fornecer instruções de desenvolvimento._

## requirements.txt

Um `requirements.txt` foi gerado automaticamente a partir do ambiente virtual `.venv_Martelo`. Mantém o ficheiro no repositório para facilitar instalações em outros ambientes. Se desejares regenerar o ficheiro localmente, executa:

```powershell
.\.venv_Martelo\Scripts\python.exe -m pip freeze > requirements.txt
```

Se for para produção, analisa e fixe versões críticas manualmente antes do deploy.

## Empacotar / criar executável (build_exe.bat)

O repositório inclui um `build_exe.bat` que pode ser usado como ponto de partida para gerar um executável Windows usando ferramentas como `PyInstaller` ou utilitários personalizados. Exemplo genérico usando `PyInstaller`:

1. Ativa o ambiente virtual e instala PyInstaller:

```powershell
.\.venv_Martelo\Scripts\Activate.ps1
pip install pyinstaller
```

2. Exemplo de comando PyInstaller (gera pasta `dist\Martelo_Orcamentos_V2`):

```powershell
pyinstaller --noconfirm --onefile --windowed --name Martelo_Orcamentos_V2 Martelo_Orcamentos_V2\run_dev.py
```

3. O ficheiro `build_exe.bat` pode conter passos adicionais (copiar ficheiros estáticos, templates, licenças, criar atalho). Um exemplo simples que podes usar/ajustar:

```bat
@echo off
call ".\.venv_Martelo\Scripts\Activate.ps1"
pyinstaller --noconfirm --onefile --windowed --name Martelo_Orcamentos_V2 Martelo_Orcamentos_V2\run_dev.py
if %errorlevel% neq 0 (
	echo Build failed
	exit /b %errorlevel%
)
echo Build succeeded. Check the 'dist' folder for the executable.
```

4. Testar o executável gerado abrindo `dist\Martelo_Orcamentos_V2.exe`. Se o teu projeto usa ficheiros adicionais (templates, UI `.ui`, assets), garante que são incluídos no bundle do PyInstaller (`--add-data "src;dest"`) ou copiados manualmente após o build.

5. Nota: para builds estáveis em CI/produção, considera usar um ambiente limpo (por exemplo um container Docker ou runner dedicado) para evitar dependências indesejadas no executável.

---
Se queres, eu:
- adiciono um `requirements.txt` ao repositório (já gerado localmente),
- acrescento um `build_exe.bat` de exemplo (ou atualizo o existente) contendo o script de PyInstaller,
- ou actualizo o README com instruções mais específicas para inclusão de assets.