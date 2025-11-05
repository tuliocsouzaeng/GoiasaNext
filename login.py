# login.py
import streamlit as st

def show_login():
    st.title("🔐 Login")

    # Carrega credenciais
    credentials = st.secrets.get("credentials", {})

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if username in credentials:
                user_data = credentials[username]
                if user_data.get("senha") == password:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.session_state["nome"] = user_data.get("nome", username.title())
                    st.success(f"Bem-vindo, **{st.session_state['nome']}**!")
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")