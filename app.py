import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Conectando ao MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["daily_db"]
email_collection = db["emails"]
response_collection = db["responses"]

# Função para validar o e-mail
def email_existe(email):
    return email_collection.find_one({"email": email}) is not None

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
            "data": data.isoformat(),
            "tarefa_realizada": tarefa_realizada,
            "progresso": progresso,
            "descricao_obstaculos": descricao_obstaculos,
            "proximas_etapas": proximas_etapas,
            "comentarios_adicionais": comentarios_adicionais
        }
        response_collection.insert_one(response)
        st.success("Formulário enviado com sucesso!")

# Controlando a navegação entre as páginas
if "email_validado" not in st.session_state:
    st.session_state.email_validado = False

if st.session_state.email_validado:
    formulario_daily()
else:
    pagina_inicial()
