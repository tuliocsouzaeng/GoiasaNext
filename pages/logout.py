import streamlit as st

# Proteção (redireciona se não estiver logado)
if not st.session_state.get("authenticated", False):
    st.warning("Você precisa estar logado.")
    st.switch_page("index.py")

st.title("Sair do Sistema")

# Nome do usuário
nome = st.session_state.get("nome", st.session_state.get("username", "Usuário")).title()
st.write(f"{nome}, clique no botão abaixo para sair do Goiasa Next.")

# Botão vermelho simples
if st.button("Sair", type="primary", help="Clique para fazer logout"):
    st.session_state["authenticated"] = False
    st.session_state.pop("username", None)
    st.session_state.pop("nome", None)
    st.rerun()