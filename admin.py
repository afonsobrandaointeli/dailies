import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
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

# Definindo o token único para todos os administradores
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# Carregar e-mails dos administradores do arquivo .env
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS").split(',')

# Função para verificar se é um administrador
def is_admin(email, token):
    return email in ADMIN_EMAILS and token == ADMIN_TOKEN

# Página inicial do formulário
def pagina_inicial():
    st.title("Verificação de Administrador")

    email = st.text_input("Digite seu e-mail")
    token = st.text_input("Digite o token", type="password")

    if st.button("Verificar Administrador"):
        if is_admin(email, token):
            st.session_state.email_validado = True
            st.session_state.email = email
            st.experimental_rerun()  # Redireciona automaticamente para o dashboard
        else:
            st.error("E-mail ou token inválido. Tente novamente.")

# Página do dashboard
def dashboard():
    st.title("Dashboard de Resultados")

    # Carregar os dados das respostas
    responses = pd.DataFrame(list(response_collection.find()))

    # Exibição de e-mails com filtros
    st.subheader("E-mails Cadastrados")
    emails = pd.DataFrame(list(email_collection.find()), columns=["email", "grupo", "turma"])

    # Filtros
    grupo = st.selectbox("Filtrar por Grupo", options=["Todos"] + emails["grupo"].unique().tolist())
    turma = st.selectbox("Filtrar por Turma", options=["Todos"] + emails["turma"].unique().tolist())

    if grupo != "Todos":
        emails = emails[emails["grupo"] == grupo]
    if turma != "Todos":
        emails = emails[emails["turma"] == turma]

    with st.container():
        st.dataframe(emails)

    if grupo != "Todos":
        responses = responses[responses['email'].isin(emails[emails['grupo'] == grupo]['email'])]
    if turma != "Todos":
        responses = responses[responses['email'].isin(emails[emails['turma'] == turma]['email'])]

    if 'data' in responses.columns:
        # Série temporal de inputs por dia
        responses['data'] = pd.to_datetime(responses['data'])
        daily_counts = responses.groupby(responses['data'].dt.date).size().reset_index(name='counts')

        st.subheader("Série Temporal de Inputs por Dia")
        fig = px.bar(daily_counts, x='data', y='counts', labels={'data': 'Data', 'counts': 'Quantidade de Inputs'})
        st.plotly_chart(fig)
    else:
        st.warning("Nenhuma entrada de dados encontrada.")

    # Gráfico de barras acumulativas para o progresso das tarefas por semana do ano
    if 'progresso' in responses.columns:
        st.subheader("Distribuição do Progresso das Tarefas por Semana do Ano")
        responses['week'] = responses['data'].dt.isocalendar().week
        progresso_counts = responses.groupby(['week', 'progresso']).size().reset_index(name='counts')
        fig_stacked = px.bar(progresso_counts, x='week', y='counts', color='progresso', labels={'week': 'Semana do Ano', 'counts': 'Quantidade', 'progresso': 'Progresso'})
        st.plotly_chart(fig_stacked)
    else:
        st.warning("Nenhuma entrada de dados encontrada para o progresso.")

    # Tabela de quantidade de dailies por aluno
    st.subheader("Quantidade de Dailies por Aluno")
    if 'email' in responses.columns:
        dailies_por_aluno = responses['email'].value_counts().reset_index()
        dailies_por_aluno.columns = ['Email', 'Quantidade de Dailies']
        with st.container():
            st.dataframe(dailies_por_aluno)
    else:
        st.warning("Nenhuma entrada de dados encontrada para os e-mails.")

# Controlando a navegação entre as páginas
if "email_validado" not in st.session_state:
    st.session_state.email_validado = False

if st.session_state.email_validado:
    dashboard()
else:
    pagina_inicial()
