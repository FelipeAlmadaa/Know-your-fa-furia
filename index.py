import streamlit as st
import pandas as pd
import os
import pytesseract
from PIL import Image
import re
from unidecode import unidecode
import requests
from datetime import datetime
import json
import google.generativeai as genai


# Configurar o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'

# Constantes
genai.configure(api_key=st.secrets["genai_api_key"])
CSV_FILE = "dados_fas.csv"
BEARER_TOKEN = st.secrets["bearer_api_token"]
FURIA_USER_ID = "894704535037513729"  # ID oficial da conta da FURIA

# Função para salvar os dados no CSV
def salvar_dados(dados):
    if not os.path.isfile(CSV_FILE):
        df = pd.DataFrame([dados])
        df.to_csv(CSV_FILE, index=False)
    else:
        df = pd.DataFrame([dados])
        df.to_csv(CSV_FILE, mode='a', header=False, index=False)


def salvar_arquivos(uploaded_file_frente, uploaded_file_verso, cpf):
    if not os.path.exists("documentos"):
        os.makedirs("documentos")
    
    caminhos = []
    try:
        if uploaded_file_frente is not None:
            frente_path = f"documentos/{cpf}_frente.{uploaded_file_frente.name.split('.')[-1]}"
            with open(frente_path, "wb") as f:
                f.write(uploaded_file_frente.getbuffer())
            caminhos.append(frente_path)
        
        if uploaded_file_verso is not None:
            verso_path = f"documentos/{cpf}_verso.{uploaded_file_verso.name.split('.')[-1]}"
            with open(verso_path, "wb") as f:
                f.write(uploaded_file_verso.getbuffer())
            caminhos.append(verso_path)
            
        return caminhos
    except Exception as e:
        st.error(f"Erro ao salvar arquivos: {str(e)}")
        return None
         
# Função para processar o texto OCR (somente retornar o texto completo)
def processar_texto_ocr(texto):
    texto = unidecode(texto)
    return {
        'texto_original': texto
    }
    
def processar_texto_ocr(texto):
    """Processa o texto extraído pelo OCR"""
    texto = unidecode(texto)
    return {'texto_original': texto}


    
def extrair_username_twitter(input_twitter):
    """Extrai o username do Twitter independente do formato informado"""
    if not input_twitter:
        return None
    
    username = input_twitter.strip().lstrip('@')
    
    if 'twitter.com/' in username:
        username = username.split('twitter.com/')[-1].split('/')[0].split('?')[0]
    
    username = username.lstrip('@')
    return username if username else None

def obter_id_usuario_twitter(username: str, BEARER_TOKEN: str) -> str:
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()['data']['id']
    else:
        print(f"Erro {response.status_code}: {response.text}")
        return None
    

def buscar_tweets_furia(user_id: str, BEARER_TOKEN: str, max_results: int = 5) -> list:
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }
    params = {
        "max_results": max_results,
        "tweet.fields": "created_at,text"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        dados = response.json()
        return [{
            "id": tweet["id"],
            "text": tweet["text"],
            "created_at": tweet.get("created_at", "")
        } for tweet in dados.get("data", [])]
    else:
        print(f"Erro {response.status_code}: {response.text}")
        return []


def analisar_twitter(username):
    """Analisa o perfil do Twitter usando a API v2"""
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    resultados = {
        'menciona_bio': False,
        'tweets_furia': [],
        'segue_furia': False,
        'seguindo': [],
        'bio': "",
        'tweets': []
    }

    try:
        # 1. Obter informações básicas do usuário
        url_user = f"https://api.twitter.com/2/users/by/username/{username}?user.fields=description"
        resp_user = requests.get(url_user, headers=headers)
        
        if resp_user.status_code != 200:
            st.error(f"Erro ao acessar perfil: {resp_user.json().get('detail', 'Erro desconhecido')}")
            return resultados

        user_data = resp_user.json().get("data", {})
        user_id = user_data.get("id")
        resultados['bio'] = user_data.get("description", "")
        resultados['menciona_bio'] = "furia" in resultados['bio'].lower()

        # 2. Buscar tweets sobre FURIA
        resultados['tweets_furia'] = buscar_tweets_furia(user_id, BEARER_TOKEN)

        # 3. Verificar se segue a FURIA
        url_seguindo = f"https://api.twitter.com/2/users/{user_id}/following?max_results=1000"
        resp_following = requests.get(url_seguindo, headers=headers)
        
        if resp_following.status_code == 200:
            seguindo = resp_following.json().get("data", [])
            resultados['seguindo'] = [user['username'] for user in seguindo]
            resultados['segue_furia'] = any(user.get("id") == FURIA_USER_ID for user in seguindo)

    except Exception as e:
        st.error(f"Erro na análise do Twitter: {str(e)}")

    return resultados


# Título da página
st.set_page_config(page_title="Know Your Fan", page_icon="🎮")
st.markdown("<h1 style='text-align: center;'>🎮 Know Your Fan - Furia</h1>", unsafe_allow_html=True)

# Inicialização da sessão
if 'dados_fan' not in st.session_state:
    st.session_state['dados_fan'] = {}
    
# Tabs principais
abas = st.tabs(["📌 Cadastro", "🪪 Documento", "🌐 Redes Sociais", "🎮 Atividades"])

# --- ABA 1: Cadastro ---
with abas[0]:
    with st.form("formulario_fan"):
        st.subheader("📌 Informações Pessoais")
        nome = st.text_input("Nome completo*", placeholder="Como no documento", value=st.session_state['dados_fan'].get('Nome', ''))
        cpf = st.text_input("CPF*", placeholder="Somente números", value=st.session_state['dados_fan'].get('CPF', ''))
        endereco = st.text_input("Endereço completo", value=st.session_state['dados_fan'].get('Endereço', ''))
        email = st.text_input("E-mail*", value=st.session_state['dados_fan'].get('E-mail', ''))
        enviado = st.form_submit_button("Enviar Cadastro")
        
        if enviado:
            if not nome or not cpf or not email:
                st.error("Por favor, preencha todos os campos obrigatórios (marcados com *)")
            else:
                st.session_state['dados_fan'].update({
                    "Nome": nome,
                    "CPF": cpf,
                    "Endereço": endereco,
                    "E-mail": email
                })
                st.success("✅ Informações pessoais salvas!")

# --- ABA 2: Documento ---
with abas[1]:
    st.subheader("🪪 Validação de Documento")
    st.info("""
    Envie uma imagem legível da frente do seu RG ou CNH. A imagem deve estar:
    - Nítida, com boa iluminação
    - Sem cortes ou sombras
    - Com todos os dados visíveis
    """)
    uploaded_file_frente = st.file_uploader("📷 Imagem  **1** ", type=["png", "jpg", "jpeg"], key="frente")
    uploaded_file_verso = st.file_uploader("📷 Imagem **2** do documento (opcional)", type=["png", "jpg", "jpeg"], key="verso")

    if uploaded_file_frente is not None:
        try:
            with st.spinner('Processando documento...'):
                image_frente = Image.open(uploaded_file_frente).convert('L')
                texto_frente = pytesseract.image_to_string(image_frente, config='--oem 3 --psm 6 -l por')
                texto_verso = ""
                image_verso = None
                if uploaded_file_verso is not None:
                    image_verso = Image.open(uploaded_file_verso).convert('L')
                    texto_verso = pytesseract.image_to_string(image_verso, config='--oem 3 --psm 6 -l por')
                texto_extraido = texto_frente + "\n" + texto_verso
                dados_doc = processar_texto_ocr(texto_extraido)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("🖼️ Documento processado")
                st.image(image_frente, caption="Frente do documento", use_container_width=True)
                if image_verso:
                    st.image(image_verso, caption="Verso do documento", use_container_width=True)

            with col2:
                st.subheader("📋 Validação com base no texto OCR")
                texto_upper = unidecode(dados_doc['texto_original']).upper()
                nome_ok = unidecode(st.session_state['dados_fan']['Nome']).upper() in texto_upper
                cpf_ok = re.sub(r'\D', '', st.session_state['dados_fan']['CPF']) in re.sub(r'\D', '', dados_doc['texto_original'])
                cpf_limpo = re.sub(r'\D', '', cpf)
               
                # Salvar arquivos
                caminhos = salvar_arquivos(uploaded_file_frente, uploaded_file_verso, st.session_state['dados_fan']['CPF'])
                 
                if caminhos:
                    st.session_state['dados_fan']['Documento_Frente'] = caminhos[0]
                    if len(caminhos) > 1:
                        st.session_state['dados_fan']['Documento_Verso'] = caminhos[1]
                    
                    st.session_state['dados_fan']['Doc_Validado'] = nome_ok and cpf_ok
                    st.session_state['dados_fan']['OCR_Texto'] = dados_doc['texto_original']
                    
                    st.success("✅ Documento processado e salvo!")
                    st.json({
                        "Nome_Encontrado": nome_ok,
                        "CPF_Encontrado": cpf_ok,
                        "Arquivos_Salvos": caminhos
                    })
                    
                st.markdown(f"**Nome encontrado no texto:** {'✅ Sim' if nome_ok else '❌ Não'}")
                st.markdown(f"**CPF encontrado no texto:** {'✅ Sim' if cpf_ok else '❌ Não'}")

                if nome_ok and cpf_ok:
                    st.success("✅ Documento validado com sucesso com base no nome e CPF!")
                else:
                    if not nome_ok:
                        st.warning("⚠ Nome do formulário não foi encontrado no texto do documento.")
                    if not cpf_ok:
                        st.warning("⚠ CPF do formulário não foi encontrado no texto do documento.")

            with st.expander("📄 Texto OCR completo"):
                st.text(dados_doc['texto_original'])

        except Exception as e:
            st.error(f"❌ Erro ao processar o documento: {str(e)}")

# --- ABA 3: Redes Sociais ---
with abas[2]:
    st.subheader("🌐 Redes Sociais")
    twitter = st.text_input("Twitter", placeholder="@username ou https://twitter.com/username", 
                            help="Você pode informar apenas @username")
    processar_redes = st.button("Processar Perfil Baseado em Redes Sociais")

    if twitter and processar_redes:
        username = extrair_username_twitter(twitter)
        if username:
            st.subheader(f"🔍 Análise do Twitter @{username}")
            with st.spinner('Analisando perfil no Twitter...'):
                analise = analisar_twitter(username)

                st.markdown("### 📋 Resultados da Análise")
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.metric("Menciona FURIA na bio", "✅ Sim" if analise['menciona_bio'] else "❌ Não")
                    st.metric("Segue a FURIA", "✅ Sim" if analise['segue_furia'] else "❌ Não")
                with col_res2:
                    st.metric("Tweets sobre FURIA", len(analise['tweets_furia']))
                    st.metric("Contas seguidas", len(analise['seguindo']))

                with st.expander("📝 Bio do perfil"):
                    st.write(analise.get('bio', 'Nenhuma bio disponível'))

                with st.expander("🐦 Tweets sobre FURIA"):
                    if analise['tweets_furia']:
                        for tweet in analise['tweets_furia']:
                            tweet_url = f"https://twitter.com/{username}/status/{tweet['id']}"
                            data_tweet = tweet['created_at'][:10] if tweet['created_at'] else "Data não disponível"
                            st.markdown(f"**{data_tweet}**: [{tweet['text']}]({tweet_url})")
                    else:
                        st.info("Nenhum tweet sobre FURIA encontrado")

                with st.expander("👥 Contas seguidas (top 20)"):

                    if analise['seguindo']:
                        st.write(", ".join(analise['seguindo'][:20]))
                    else:
                        st.info("Não foi possível obter a lista de contas seguidas")
                
                # Salvar as informações na sessão
                st.session_state['analise_twitter'] = analise
                
        else:
            st.warning("Formato inválido do Twitter. Use @username ou o link completo.") 

    # Botão para salvar tudo
    if st.button("Salvar Tudo", key="salvar_tudo"):
        dados_atualizados = {
            "Twitter": twitter,
        }

        if 'analise_twitter' in st.session_state:
            dados_atualizados.update({
                "Twitter_Analise": {
                    "bio": st.session_state['analise_twitter']['bio'],
                    "menciona_bio": st.session_state['analise_twitter']['menciona_bio'],
                    "segue_furia": st.session_state['analise_twitter']['segue_furia'],
                    "tweets_furia": st.session_state['analise_twitter']['tweets_furia'],
                    "seguindo": st.session_state['analise_twitter']['seguindo'],
                }
            })

        st.session_state['dados_fan'].update(dados_atualizados)
        st.success("✅ Todos os dados foram salvos!")


# --- ABA 4: Atividades ---
with abas[3]:
    st.subheader("🎮 Atividades de e-sports")

    from google import genai

    # Configurando a API com sua chave secreta
    client = genai.Client(api_key=st.secrets["genai_api_key"])

    # Campos de entrada
    col3, col4 = st.columns(2)
    with col3:
        eventos = st.text_area("Eventos participados", value=st.session_state['dados_fan'].get('Eventos', ''))
    with col4:
        compras = st.text_area("Compras relacionadas", value=st.session_state['dados_fan'].get('Compras', ''))

    # Atualizando os dados na sessão
    if eventos and compras:
        st.session_state['dados_fan']['Eventos'] = eventos
        st.session_state['dados_fan']['Compras'] = compras

    # Botão para gerar recomendações
    processar_atividades = st.button("Encontrar recomendações")

    if processar_atividades:
        prompt = f"""
        Com base nestas informações de um fã de e-sports:

        Eventos participados:
        {eventos}

        Compras relacionadas:
        {compras}

        Quais recomendações de sites, conteúdos ou produtos você sugeriria para ele?
        """

    try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
            recomendacoes = response.text.strip()

            # Mostra na interface
            st.subheader("🔎 Recomendações da IA:")
            st.write(recomendacoes)

            # Salva no estado da sessão
            st.session_state['dados_fan']['Recomendacoes'] = recomendacoes

    except Exception as e:
        # st.error(f"❌ Erro ao gerar recomendações: {e}")
        st.spinner("Aguardando solicitação...")
    
# --- Salvar Dados ao final ---
if st.button("✅ Salvar Cadastro Completo", use_container_width=True):
    if not all(key in st.session_state['dados_fan'] for key in ['Nome', 'CPF', 'E-mail']):
        st.error("Complete todas as seções obrigatórias antes de finalizar")
    else:
        try:
            # Adiciona data/hora
            st.session_state['dados_fan']['Data_Cadastro'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Salva no CSV
            salvar_dados(st.session_state['dados_fan'])
            
            # Salva cópia completa em JSON
            cpf_limpo = re.sub(r'\D', '', st.session_state['dados_fan']['CPF'])
            json_path = f"documentos/{cpf_limpo}_cadastro_completo.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(st.session_state['dados_fan'], f, ensure_ascii=False, indent=2)
            
            st.balloons()
            st.success("🎉 Cadastro completo salvo com sucesso!")
            
            # Opção para visualizar dados
            with st.expander("Visualizar Dados Salvos"):
                st.json(st.session_state['dados_fan'])
            
            # Limpa sessão
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        except Exception as e:
            st.error(f"Erro ao salvar cadastro: {str(e)}")

