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
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}
    url = "https://bioms-api-backend.onrender.com/lista-exercicios"
    
    try:
        # Aumentado para 30 segundos para dar tempo ao Render de "acordar"
        res = requests.get(url, headers=cabecalho, timeout=30) 
        if res.status_code == 200:
            return res.json()
        return []
    except:
        return []

def consultar_media_normativa(exercicio, sexo, idade):
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}
    url = "https://bioms-api-backend.onrender.com/consulta-normativa"
    
    payload = {"exercicio": exercicio, "sexo": sexo, "idade": int(idade)}
    try:
        # Aumentado para 30 segundos
        res = requests.post(url, json=payload, headers=cabecalho, timeout=30)
        if res.status_code == 200:
            return res.json()
        return {"erro": "Falha na API"}
    except:
        return {"erro": "Sem conexão"}