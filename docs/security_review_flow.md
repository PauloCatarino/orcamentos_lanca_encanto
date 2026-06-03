# Fluxo De Revisao De Seguranca

## Objetivo

Definir um fluxo curto, repetivel e adaptado ao Martelo V2 para rever alteracoes com impacto em seguranca, integridade de dados e risco de regressao funcional.

No Martelo, "seguranca" nao significa apenas segredos ou acessos. Tambem inclui:

- integridade dos calculos
- consistencia entre Dados Gerais, Dados Items e Edicao Local
- estabilidade da `tab_custeio_items`
- compatibilidade com orcamentos antigos
- seguranca de automacoes, ficheiros, logs e integracoes

## Quando Aplicar

Aplicar sempre antes de:

- criar release
- gerar executavel ou instalador
- aprovar alteracoes em servicos de calculo ou persistencia
- mexer em integracoes externas, paths de rede, Excel, PDF ou automacoes Windows

Nota:

- `release.bat` ja corre a revisao local de seguranca por omissao antes do build
- para ignorar esse gate numa excecao controlada, usar `--skip-security-review`

## Classificacao De Risco

### Alto risco

- `Martelo_Orcamentos_V2/app/services/custeio_items.py`
- `Martelo_Orcamentos_V2/app/services/dados_gerais.py`
- `Martelo_Orcamentos_V2/app/services/dados_items.py`
- `Martelo_Orcamentos_V2/app/services/def_pecas.py`
- `Martelo_Orcamentos_V2/app/services/modulos.py`
- `Martelo_Orcamentos_V2/app/services/orcamentos.py`
- `Martelo_Orcamentos_V2/app/services/cutrite_automation.py`
- `Martelo_Orcamentos_V2/app/services/producao_preparacao.py`
- `Martelo_Orcamentos_V2/app/db.py`
- `Martelo_Orcamentos_V2/app/config.py`
- `Martelo_Orcamentos_V2/app/services/phc_sql.py`
- `Martelo_Orcamentos_V2/app/services/streamlit_sql.py`

### Medio risco

- formularios e models Qt que escrevem no item ou no custeio
- scripts de release e build
- servicos de relatorios, pesquisa e importacao

### Baixo risco

- documentacao
- texto, labels e pequenos ajustes visuais sem efeito em dados ou calculo

## Fluxo Operativo

### 1. Classificar a alteracao

Antes de rever, responder:

- toca em calculo, custeio, BD, automacao, ficheiros ou credenciais?
- altera o fluxo dos 3 niveis de regra?
- pode afetar orcamentos antigos?

Se a resposta for "sim" a qualquer uma, tratar como pelo menos medio risco.

### 2. Fazer auto-revisao curta

Usar a checklist em [security_change_checklist.md](/C:/Users/Utilizador/Documents/Martelo_Orcamentos_V2/docs/security_change_checklist.md).

### 3. Correr revisao local base

Comando rapido:

```powershell
.\security_review.bat
```

Comando recomendado antes de release oficial:

```powershell
.\security_review.bat -FullPytest -Strict
```

O comando faz:

- corre a suite critica de testes por omissao
- permite correr a suite completa com `-FullPytest`
- faz scan local de padroes de risco como `eval`, `exec`, `shell=True`, `yaml.load` e segredos hardcoded
- tenta usar `bandit`, `pip-audit` e `detect-secrets` se estiverem instalados

No fluxo de release, o equivalente e:

```powershell
.\release.bat patch
```

Opcoes uteis:

```powershell
.\release.bat patch --full-security-review
.\release.bat patch --strict-security-review
.\release.bat patch --skip-security-review
```

### 4. Correr testes dirigidos pela area alterada

Se a alteracao tocar em:

- `custeio_items`, `dados_gerais`, `dados_items`, `def_pecas`, `modulos`
  - correr tambem `tests/test_custeio_items_model.py`
  - correr `tests/test_mat_default_filtering.py`
  - correr `tests/test_orla_pricing.py`
  - correr `tests/test_margens.py`
  - correr `tests/test_def_pecas_restore.py`
  - correr `tests/test_modulos_referencia.py`

- `cutrite_automation`, exportacao Excel, automacao Windows
  - correr `tests/test_cutrite_automation.py`

- `db.py`, `config.py`, bootstrap de base de dados
  - correr `tests/test_db_bootstrap.py`

- release, build, instalador
  - correr `tests/test_release_tools.py`

- workflows de orcamento ou producao
  - acrescentar os testes `tests/test_orcamentos_*`
  - acrescentar os testes `tests/test_producao_*`

Exemplo:

```powershell
.\security_review.bat -AdditionalPytest tests/test_producao_preparacao.py
```

### 5. Fazer validacao manual curta

Para alteracoes de medio ou alto risco, validar manualmente um cenario real:

1. abrir um orcamento de teste
2. alterar Dados Gerais
3. alterar Dados Item
4. fazer uma edicao local em custeio
5. confirmar que calculo, materiais, ferragens e totais continuam coerentes

Se a alteracao tocar em automacao ou ficheiros:

1. testar um ficheiro valido
2. testar ficheiro bloqueado ou path invalido
3. confirmar que logs e mensagens de erro nao expoem segredos

## Gates De Aprovacao

Nao aprovar release se existir algum destes pontos:

- testes relevantes a falhar
- segredo, password, token ou `DB_URI` exposto no codigo ou logs
- SQL construido por concatenacao sem validacao
- novo uso de `eval`, `exec` ou `shell=True` sem justificacao tecnica e revisao manual
- alteracao que quebre a heranca entre Dados Gerais, Dados Items e Edicao Local
- risco de corromper `tab_custeio_items`
- incompatibilidade conhecida com orcamentos antigos sem plano de migracao

## Observacoes Especificas Do Martelo V2

- O uso de formulas e medidas em texto deve ser tratado como area sensivel.
- Qualquer alteracao em logs deve garantir mascaramento de credenciais.
- Operacoes em shares de rede, Excel, PDF e automacao Windows devem ser revistas como risco operacional.
- A prioridade maxima continua a ser integridade do custeio e estabilidade dos items.

## Ferramentas Recomendadas

Se quiser ativar todas as verificacoes opcionais no ambiente local:

```powershell
.\.venv_Martelo\Scripts\python.exe -m pip install bandit pip-audit detect-secrets
```

Depois disso, usar:

```powershell
.\security_review.bat -FullPytest -Strict
```
