import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login


st.title("Goiasa Next")
nome = st.session_state.get("nome", st.session_state.get("username", "Usuário")).title()
st.write(f"{nome}, bem-vindo ao sistema de Gestão de Equipamentos da Goiasa!")

with st.expander("Como usar o sistema"):
    st.write("- Navegue pelas seções na barra lateral.")
    st.write("- Visualize dados de equipamentos em cada módulo.")
