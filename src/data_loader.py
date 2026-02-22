import os
import requests

# Este é o endereço onde sua API (main.py) está "escutando"
API_URL = "https://bioms-api-backend.onrender.com/calcular"

def chamar_api_bioms(dados_atleta):
    """
    Pega os dados do Streamlit e envia para a API calcular, mostrando o crachá de segurança.
    """
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}

    try:
        response = requests.post(API_URL, json=dados_atleta, headers=cabecalho, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"erro": f"Erro na API: {response.status_code}", "detalhe": response.text}
    except Exception as e:
        return {"erro": "Não consegui falar com a API. Verifique se o terminal da API está ligado!"}

def obter_lista_exercicios():
    """Pergunta para a API quais exercícios existem no banco"""
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}
    url = "https://bioms-api-backend.onrender.com/lista-exercicios"
    
    try:
        res = requests.get(url, headers=cabecalho, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except:
        return []

def consultar_media_normativa(exercicio, sexo, idade):
    """Pergunta para a API a média de um exercício específico"""
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}
    url = "https://bioms-api-backend.onrender.com/consulta-normativa"
    
    payload = {"exercicio": exercicio, "sexo": sexo, "idade": int(idade)}
    try:
        res = requests.post(url, json=payload, headers=cabecalho, timeout=10)
        if res.status_code == 200:
            return res.json() # Retorna algo como {"media": 45.4, "desvio": 13.2}
        return {"erro": "Falha na API"}
    except:
        return {"erro": "Sem conexão"}