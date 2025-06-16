"""
descricoes_manager.py
=====================
Pequeno utilitário para armazenar e recuperar descrições pré-definidas
utilizadas no menu de contexto do campo ``plainTextEdit_descricao_orcamento``.
As descrições são guardadas num ficheiro de texto simples
(``descricoes_predefinidas.txt``) localizado na pasta do projecto.
"""
""""
import os

FILE_PATH = os.path.join(os.path.dirname(__file__), "descricoes_predefinidas.txt")


def carregar_descricoes():
    #Lê o ficheiro de descrições e retorna uma lista de strings.
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]
    return linhas


def guardar_descricoes(descricoes):
    #Guarda a lista de descrições no ficheiro associado.
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        for linha in descricoes:
            f.write(linha.strip() + "\n")

"""