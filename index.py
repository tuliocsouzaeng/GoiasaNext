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
    "Indicadores":[
        st.Page("pages/indicadores_manutencao.py", title="Indicadores da Manutenção"),
        st.Page("pages/indicadores_projetos.py", title="Indicadores dos Projetos"),
    ],
    "Estáticos": [
        st.Page("pages/tanques.py", title="Tanques"),
        st.Page("pages/vasos_de_pressao.py", title="Vasos de Pressão"),
        st.Page("pages/valvulas_de_seguranca.py", title="Válvulas de Segurança"),
        st.Page("pages/tubulacoes.py", title="Tubulações"),
        st.Page("pages/torres_de_resfriamento.py", title="Torres de Resfriamento"),
    ],
    "Dinâmicos":[
        st.Page("pages/bombas.py", title="Bombas"),
        st.Page("pages/redutores.py", title="Redutores"),
        st.Page("pages/turbinas.py", title="Turbinas"),
        st.Page("pages/acoplamentos.py", title="Acoplamentos"),
        st.Page("pages/castelos.py", title="Castelos"),
        st.Page("pages/unidades_hidraulicas.py", title="Unidades Hidráulicas"),
    ],
    "Elétricos":[
        st.Page("pages/motores.py", title="Motores de Baixa Tensão"),
    ],
    "Instrumentação":[
        st.Page("pages/transmissores.py", title="Transmissores"),
    ],
    "Busca Rápida":[
        st.Page("pages/busca_rapida_automatica.py", title="Busca Rápida Automática"),
        st.Page("pages/busca_rapida_manual.py", title="Busca Rápida Manual"),
    ],
}

# Se NÃO estiver logado → mostra tela de login
if not st.session_state["authenticated"]:
    show_login()
else:
    # Se estiver logado → mostra navegação
    pg = st.navigation(pages)
    pg.run()
