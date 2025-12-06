import os
import io
import pandas as pd
from cryptography.fernet import Fernet
import streamlit as st

# Carrega a chave dos secrets
def _get_key():
    # Primeiro tenta Render → variável de ambiente
    key = os.environ.get("DATA_KEY")
    # Depois tenta st.secrets (se você usar secrets.toml)
    if not key and "DATA_KEY" in st.secrets:
        key = st.secrets["DATA_KEY"]

    if not key:
        raise RuntimeError("Chave DATA_KEY não encontrada.")

    return key.encode() if isinstance(key, str) else key


# Cria o objeto Fernet apenas uma vez (cacheado)
@st.cache_resource
def _get_fernet():
    return Fernet(_get_key())


# Função pública para carregar CSV criptografado
@st.cache_data
def load_csv(path: str, **pd_kwargs):
    """
    Lê um arquivo CSV criptografado (.enc) e retorna um DataFrame.
    pd_kwargs são repassados para pd.read_csv().
    Exemplo:
        df = load_csv("data/transmissores.csv.enc", sep=";", encoding="utf-8")
    """
    fernet = _get_fernet()

    with open(path, "rb") as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted)

    # Lê o CSV direto da memória
    return pd.read_csv(io.BytesIO(decrypted), **pd_kwargs)