# index.py
import streamlit as st
from login import show_login

# Configuração da página
st.set_page_config(page_title="Goiasa Next", layout="wide")

# Verifica se o usuário está autenticado
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Se NÃO estiver logado → mostra tela de login
if not st.session_state["authenticated"]:
    show_login()
else:
    # Se estiver logado → mostra navegação
    pg = st.navigation([
        st.Page("pages/home.py", title="Página Inicial"),
        st.Page("pages/tanques.py", title="Tanques"),
        st.Page("pages/vasos_de_pressao.py", title="Vasos de Pressão"),
        st.Page("pages/tubulacoes.py", title="Tubulações"),
        st.Page("pages/logout.py", title="Sair"),
    ])
    pg.run()