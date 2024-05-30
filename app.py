import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Conectando ao PostgreSQL
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

conn = psycopg2.connect(
    host=DB_HOST,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Função para validar o e-mail
def email_existe(email):
    cursor.execute("SELECT 1 FROM emails WHERE email = %s", (email,))
    return cursor.fetchone() is not None

# Página inicial do formulário
def pagina_inicial():
    st.title("Verificação de E-mail")

    email = st.text_input("Digite seu e-mail")

    if st.button("Login"):
        if email_existe(email):
            st.session_state.email_validado = True
            st.session_state.email = email
            st.experimental_rerun()  # Redireciona automaticamente para o formulário daily
        else:
            st.error("E-mail não encontrado. Tente novamente.")

# Página do formulário da daily
def formulario_daily():
    st.title("Formulário de Daily de Tech")

    data = st.date_input("Data", datetime.now().date())
    tarefa_realizada = st.text_area("Tarefa Realizada (ou a ser realizada hoje)")
    progresso = st.radio("Progresso", ("Concluído", "Em Progresso", "Obstáculos Encontrados"))
    descricao_obstaculos = st.text_area("Descrição dos Obstáculos", disabled=progresso != "Obstáculos Encontrados")
    proximas_etapas = st.text_area("Próximas Etapas")
    comentarios_adicionais = st.text_area("Comentários Adicionais")

    if st.button("Enviar"):
        response = {
            "email": st.session_state.email,
            "data": data,
            "tarefa_realizada": tarefa_realizada,
            "progresso": progresso,
            "descricao_obstaculos": descricao_obstaculos,
            "proximas_etapas": proximas_etapas,
            "comentarios_adicionais": comentarios_adicionais
        }
        cursor.execute("""
            INSERT INTO responses (email, data, tarefa_realizada, progresso, descricao_obstaculos, proximas_etapas, comentarios_adicionais)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (response['email'], response['data'], response['tarefa_realizada'], response['progresso'], response['descricao_obstaculos'], response['proximas_etapas'], response['comentarios_adicionais']))
        conn.commit()
        st.success("Formulário enviado com sucesso!")

        # Redefinir o estado e redirecionar para a tela de e-mail
        st.session_state.email_validado = False
        st.session_state.email = None
        st.experimental_rerun()

# Controlando a navegação entre as páginas
if "email_validado" not in st.session_state:
    st.session_state.email_validado = False

if st.session_state.email_validado:
    formulario_daily()
else:
    pagina_inicial()
