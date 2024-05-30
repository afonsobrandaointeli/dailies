import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar a API do Gemini
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

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

# Definindo o token único para todos os administradores
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# Carregar e-mails dos administradores do arquivo .env
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS").split(',')

# Função para verificar se é um administrador
def is_admin(email, token):
    return email in ADMIN_EMAILS and token == ADMIN_TOKEN

# Função para carregar dados da tabela de e-mails
def carregar_emails():
    cursor.execute("SELECT email, grupo, turma FROM emails")
    return pd.DataFrame(cursor.fetchall())

# Função para carregar dados da tabela de respostas
def carregar_respostas(data_inicio, data_fim):
    query = """
    SELECT * FROM responses
    WHERE data BETWEEN %s AND %s
    """
    cursor.execute(query, (data_inicio, data_fim))
    return pd.DataFrame(cursor.fetchall())

# Função para extrair nomes dos e-mails
def extrair_nomes(emails):
    nomes = []
    for email in emails:
        nome = email.split('@')[0]
        nomes.append(nome)
    return nomes

# Função para fazer uma pergunta ao Gemini usando google.generativeai
def consultar_gemini(pergunta, dailies_text, nomes_alunos):
    try:
        model = genai.GenerativeModel('gemini-pro')
        contexto = f"Alunos: {', '.join(nomes_alunos)}\nDailies:\n{dailies_text}"
        response = model.generate_content(f"{pergunta}\nContexto: {contexto}")
        return response.text
    except Exception as e:
        st.error(f"Erro ao conectar com o Gemini: {e}")
        return "Não foi possível obter uma resposta devido a um erro de conexão."

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

    # Selecionar intervalo de datas
    data_inicio = st.date_input("Data de Início", datetime.now() - timedelta(days=30))
    data_fim = st.date_input("Data de Fim", datetime.now())

    if data_inicio > data_fim:
        st.error("Data de início não pode ser posterior à data de fim.")
        return

    # Carregar os dados das respostas
    responses = carregar_respostas(data_inicio, data_fim)

    # Exibição de e-mails com filtros
    st.subheader("E-mails Cadastrados")
    emails = carregar_emails()

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

    if not responses.empty and 'data' in responses.columns:
        # Série temporal de inputs por dia
        responses['data'] = pd.to_datetime(responses['data'])
        daily_counts = responses.groupby(responses['data'].dt.date).size().reset_index(name='counts')

        st.subheader("Série Temporal de Inputs por Dia")
        fig = px.bar(daily_counts, x='data', y='counts', labels={'data': 'Data', 'counts': 'Quantidade de Inputs'})
        st.plotly_chart(fig)

        # Gráfico de barras acumulativas para o progresso das tarefas por semana do ano
        st.subheader("Distribuição do Progresso das Tarefas por Semana do Ano")
        responses['week'] = responses['data'].dt.isocalendar().week
        progresso_counts = responses.groupby(['week', 'progresso']).size().reset_index(name='counts')
        fig_stacked = px.bar(progresso_counts, x='week', y='counts', color='progresso', labels={'week': 'Semana do Ano', 'counts': 'Quantidade', 'progresso': 'Progresso'})
        st.plotly_chart(fig_stacked)

        # Tabela de quantidade de dailies por aluno
        st.subheader("Quantidade de Dailies por Aluno")
        dailies_por_aluno = responses['email'].value_counts().reset_index()
        dailies_por_aluno.columns = ['Email', 'Quantidade de Dailies']
        with st.container():
            st.dataframe(dailies_por_aluno)

        # Pergunta ao Gemini
        st.subheader("Pergunte ao Gemini")
        st.markdown("""
        Exemplos de perguntas:
        - Quais alunos estão enfrentando mais obstáculos?
        - Qual é a próxima etapa mais comum entre os alunos?
        - Quais tarefas foram concluídas esta semana?
        """)
        pergunta = st.text_area("Digite sua pergunta:")
        if st.button("Consultar Gemini"):
            dailies_text = responses[['tarefa_realizada', 'progresso', 'descricao_obstaculos', 'proximas_etapas', 'comentarios_adicionais']].apply(lambda x: ' '.join(x.dropna().astype(str)), axis=1).tolist()
            dailies_text = ' '.join(dailies_text)
            nomes_alunos = extrair_nomes(emails['email'])
            resposta_gemini = consultar_gemini(pergunta, dailies_text, nomes_alunos)
            st.write("Resposta do Gemini:")
            st.write(resposta_gemini)

    else:
        st.warning("Nenhuma entrada de dados encontrada.")

# Controlando a navegação entre as páginas
if "email_validado" not in st.session_state:
    st.session_state.email_validado = False

if st.session_state.email_validado:
    dashboard()
else:
    pagina_inicial()
