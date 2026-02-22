import os
import pandas as pd
import streamlit as st
import requests

# Endereço da sua API para buscar o banco de dados
API_URL = "https://bioms-api-backend.onrender.com/referencia-elite"

@st.cache_data(show_spinner="Baixando base de elite da nuvem...", ttl="2h")
def load_data():
    """
    Busca a base de elite já calculada pela API, usando o crachá de segurança.
    """
    senha_secreta = os.environ.get("API_KEY_SECRETA", "BioMS_Ultra_Token_2026")
    cabecalho = {"X-API-KEY": senha_secreta}

    try:
        # Pede os dados para a API e mostra o crachá
        response = requests.get(API_URL, headers=cabecalho, timeout=15)
        
        if response.status_code == 200:
            dados = response.json()
            df = pd.DataFrame(dados)
            
            if df.empty:
                st.warning("⚠️ O banco de elite do Supabase está vazio.")
            return df
        else:
            st.error(f"Erro na API: Código {response.status_code}")
            return pd.DataFrame()
            
    except requests.exceptions.RequestException as e:
        st.error("🚨 CRÍTICO: Não foi possível conectar à API.")
        return pd.DataFrame()