# Checklist Curta De Seguranca

Usar esta checklist em cada alteracao antes de commit, PR ou release.

- [ ] A alteracao respeita os 3 niveis de regra: Dados Gerais, Dados Items e Edicao Local.
- [ ] Nao quebra a logica modular nem a estabilidade da `tab_custeio_items`.
- [ ] Nao introduz password, token, API key, `DB_URI` ou outro segredo hardcoded.
- [ ] Nao expoe dados sensiveis em logs, erros, exportacoes ou ficheiros temporarios.
- [ ] Nao introduz SQL concatenado, `exec`, `shell=True` ou novo `eval` sem revisao manual.
- [ ] Paths, ficheiros e automacoes foram validados para erro, ficheiro bloqueado e path invalido.
- [ ] Existe teste novo ou atualizado para a regressao principal da alteracao.
- [ ] Corri `.\security_review.bat` e revi os avisos.
- [ ] Se a alteracao for de medio ou alto risco, fiz validacao manual num cenario real.
- [ ] Nao ha finding critico aberto antes de release.
