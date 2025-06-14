Dentro de cada uma das 4 tabelas dados gerais existe um botão 'Escolher' que abre uma nova janela com a lista materias primas, mas se o utilizador não escolher qualquer material na tabela materias primas, sair sem selecção de material existe uma mensagem ao utilizador 'Nenhuma Ferragens foi selecionado' | 'Nenhum Material foi selecionado' | ''Nenhum sistemas_correr foi selecionado' | 'Nenhuma acabamentos foi selecionado'. Pretendo remover esta mensagem para o utilizador, deixou de fazer sentido. o utilizador se não selecionar nenhum material sai e não mostra nenhuma mensagem.

Podes rever novamente o codigo na tabela dados gerais para Sistemas Correr na coluna 'tipo' deve ficar em vazio, sem preenchimento o combobox, quando na coluna 0 'sistemas_correr' encontrar os seguintes textos:

        'SC_Painel_Porta_Correr_1' 
        'SC_Painel_Porta_Correr_2' 
        'SC_Painel_Porta_Correr_3' 
        'SC_Painel_Porta_Correr_4' 
        'SC_Espelho_Porta_Correr_1' 
        'SC_Espelho_Porta_Correr_2'
   
Eu ja estive este opção a funcionar mas agora esta novamente a preencher a coluna 'tipo' em todas as linhas com 'ROUPEIROS CORRER' deve rever o código para não preencher todas as linhas.

Mais uma alteração na tabela dados gerais sistemas correr, a coluna 'familia' atualmente esta preencher em todas as linhas 'FERRAGENS' pode alterar para escrever apenas 'PLACAS' quando na coluna 0 'sistemas_correr' encontrares :
'SC_Painel_Porta_Correr_1' 
        'SC_Painel_Porta_Correr_2' 
        'SC_Painel_Porta_Correr_3' 
        'SC_Painel_Porta_Correr_4' 
        'SC_Espelho_Porta_Correr_1' 
        'SC_Espelho_Porta_Correr_2'

Na pratica e resumo quando encontrar estes textos na coluna 0, na coluna 'tipo' fica em vazio & na coluna ' familia' escreve 'PLACAS'.

Tenho reparado que no terminal aparece umas boas centenas de linhas :
'QTableWidget: cannot insert an item that is already owned by another QTableWidget' o que podes estar a causar este tipo de mensagem muitas vezes repetidas.

Código github atualizado, deves responder português e código comentado.