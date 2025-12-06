# index.py
import streamlit as st
from login import show_login
# Configuração da página
st.set_page_config(page_title="Goiasa Next", layout="wide")

# Verifica se o usuário está autenticado
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

pages = {
    "Menu":[
        st.Page("pages/home.py", title="Página Inicial"),
        st.Page("pages/logout.py", title="Sair"),
    ],
    "Estáticos": [
        st.Page("pages/tanques.py", title="Tanques"),
        st.Page("pages/vasos_de_pressao.py", title="Vasos de Pressão"),
        st.Page("pages/valvulas_de_seguranca.py", title="Válvulas de Segurança"),
        st.Page("pages/tubulacoes.py", title="Tubulações"),
        st.Page("pages/torres_de_resfriamento.py", title="Torres de Resfriamento"),
    ],
    "Elétricos":[
        st.Page("pages/motores.py", title="Motores de Baixa Tensão"),
    ],
}

# Se NÃO estiver logado → mostra tela de login
if not st.session_state["authenticated"]:
    show_login()
else:
    # Se estiver logado → mostra navegação
    pg = st.navigation(pages)
    pg.run()
