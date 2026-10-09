import streamlit as st
import g4f
import edge_tts
import asyncio
import tempfile
import json
import os
import random
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
import nest_asyncio

nest_asyncio.apply()

# --- CONFIGURAÇÕES E BANCO DE DADOS ---
st.set_page_config(page_title="LingoTablet Premium", page_icon="💎", layout="wide")
DB_FILE = "lingo_premium_db.json"

def init_db():
    return {
        "xp": 0,
        "streak": 1,
        "last_login": str(date.today()),
        "xp_history": {str(date.today()): 0},
        "review_words": [],
        "saved_texts": [],
        "lessons_completed": 0
    }

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                hoje = str(date.today())
                if data.get("last_login") != hoje:
                    ontem = str(date.today() - timedelta(days=1))
                    if data.get("last_login") == ontem:
                        data["streak"] = data.get("streak", 1) + 1
                    else:
                        data["streak"] = 1
                    data["last_login"] = hoje
                if hoje not in data.get("xp_history", {}):
                    data["xp_history"][hoje] = 0
                return data
        except:
            return init_db()
    return init_db()

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'user_data' not in st.session_state:
    st.session_state.user_data = load_data()

def add_xp(amount):
    hoje = str(date.today())
    st.session_state.user_data["xp"] += amount
    st.session_state.user_data["xp_history"][hoje] = st.session_state.user_data["xp_history"].get(hoje, 0) + amount
    st.session_state.user_data["lessons_completed"] += 1
    save_data(st.session_state.user_data)
    st.toast(f"🌟 +{amount} XP Ganho!", icon="🚀")

# --- CSS PREMIUM ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        html, body, [class*="css"] { font-family: 'Nunito', sans-serif; }
        .stButton > button { border-radius: 12px !important; font-weight: 700 !important; transition: 0.3s; }
        .stButton > button:hover { transform: scale(1.02); }
        .premium-card { background: #1e1e24; color: white; padding: 20px; border-radius: 15px; border-left: 5px solid #00d2ff; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3);}
        .flashcard { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 50px 20px; border-radius: 20px; text-align: center; font-size: 2.5rem; font-weight: 900; box-shadow: 0 10px 20px rgba(0,0,0,0.2); margin-bottom: 20px;}
        .drive-mode { background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); padding: 40px; border-radius: 20px; text-align: center; color: #fff;}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE IA E ÁUDIO ---
def call_g4f_json(prompt):
    try:
        response = g4f.ChatCompletion.create(model=g4f.models.gpt_4, messages=[{"role": "user", "content": prompt}])
        return json.loads(response.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        st.error("Erro na comunicação com a IA. Tente novamente.")
        return None

async def generate_audio_file(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    await communicate.save(temp_file.name)
    return temp_file.name

def get_voice(lang):
    return {"Inglês": "en-US-AriaNeural", "Francês": "fr-FR-DeniseNeural", "Italiano": "it-IT-IsabellaNeural", "Espanhol": "es-ES-ElviraNeural"}.get(lang, "en-US-AriaNeural")

def recognize_audio_from_bytes(audio_bytes, lang):
    lang_codes = {"Inglês": "en-US", "Francês": "fr-FR", "Italiano": "it-IT", "Espanhol": "es-ES"}
    recognizer = sr.Recognizer()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            with sr.AudioFile(temp_audio.name) as source:
                audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data, language=lang_codes.get(lang, "en-US"))
    except Exception:
        return None

# --- BARRA LATERAL (COM O TRADUTOR RÁPIDO INTEGRADO) ---
with st.sidebar:
    st.title("💎 LingoTablet")
    st.markdown("---")
    idioma = st.selectbox("🎯 Idioma Alvo", ["Inglês", "Francês", "Italiano", "Espanhol"])
    nivel_global = st.select_slider("📈 Nível", options=["A1", "A2", "B1", "B2", "C1", "C2"], value="B1")
    
    st.markdown("---")
    
    # Tradutor Rápido embutido na barra lateral (Expander elegante)
    with st.expander(f"⚡ Tradutor Rápido ({idioma})", expanded=False):
        texto_traduzir = st.text_input("Digite a frase ou palavra:", key="quick_translate", placeholder=f"Ex: Frase em {idioma}...")
        
        if st.button("Ouvir e Traduzir", width='stretch'):
            if texto_traduzir.strip():
                with st.spinner("Traduzindo..."):
                    try:
                        prompt_trad = f'Traduza a seguinte frase do {idioma} para o português do Brasil. Retorne APENAS a tradução direta, sem aspas e sem explicações adicionais: "{texto_traduzir}"'
                        traducao_raw = g4f.ChatCompletion.create(model=g4f.models.gpt_4, messages=[{"role": "user", "content": prompt_trad}])
                        traducao = traducao_raw.replace('"', '').replace('\n', '').strip()
                        
                        st.info(f"🇧🇷 **Tradução:** {traducao}")
                        
                        voz = get_voice(idioma)
                        audio_path = asyncio.run(generate_audio_file(texto_traduzir, voz))
                        st.audio(audio_path, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"Erro: {e}")

    st.markdown("---")
    nav = st.radio("Navegação Premium", [
        "📊 Dashboard Analítico", 
        "🃏 Flashcards", 
        "📖 Leitura & Áudio", 
        "🌍 Mundo Real",
        "🎙️ Avaliador de Voz",
        "🚗 Modo Drive",
        "📄 Gerar Apostila (PDF)"
    ])

# =====================================================================
# 1. DASHBOARD ANALÍTICO AVANÇADO
# =====================================================================
if nav == "📊 Dashboard Analítico":
    st.header("Seu Centro de Inteligência")
    db = st.session_state.user_data
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌟 XP Total", db["xp"])
    col2.metric("🔥 Ofensiva", f"{db['streak']} Dias")
    col3.metric("📚 Palavras Salvas", len(db["review_words"]))
    col4.metric("🏆 Lições Feitas", db["lessons_completed"])
    
    st.markdown("---")
    st.subheader("Evolução de XP (Últimos Dias)")
    df_xp = pd.DataFrame(list(db["xp_history"].items()), columns=["Data", "XP Ganho"])
    df_xp["Data"] = pd.to_datetime(df_xp["Data"])
    df_xp = df_xp.sort_values("Data").tail(7) 
    
    if not df_xp.empty and df_xp["XP Ganho"].sum() > 0:
        fig = px.bar(df_xp, x="Data", y="XP Ganho", text_auto=True, color="XP Ganho", color_continuous_scale="Blues")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Complete lições para gerar gráficos de progresso!")

# =====================================================================
# 2. FLASHCARDS
# =====================================================================
elif nav == "🃏 Flashcards":
    st.header("Revisão Espaçada Ativa")
    words = st.session_state.user_data["review_words"]
    
    if not words:
        st.warning("Seu banco de palavras está vazio. Adicione palavras durante a Leitura!")
    else:
        if 'current_fc' not in st.session_state:
            st.session_state.current_fc = random.choice(words)
            st.session_state.show_ans = False
            
        card = st.session_state.current_fc
        if not st.session_state.show_ans:
            st.markdown(f'<div class="flashcard">{card["palavra"]}</div>', unsafe_allow_html=True)
            if st.button("🔄 Revelar Resposta", width='stretch', type="primary"):
                st.session_state.show_ans = True
                st.rerun()
        else:
            st.markdown(f'<div class="flashcard" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"><span style="font-size:1.2rem;">Tradução:</span><br>{card["traducao"]}<br><span style="font-size:1.2rem; font-style:italic;">{card["exemplo"]}</span></div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            if col1.button("❌ Errei / Esqueci", width='stretch'):
                st.session_state.pop('current_fc')
                st.rerun()
            if col2.button("✅ Lembrei (10 XP)", width='stretch'):
                add_xp(10)
                st.session_state.pop('current_fc')
                st.rerun()

# =====================================================================
# 3. LEITURA & ÁUDIO
# =====================================================================
elif nav == "📖 Leitura & Áudio":
    st.header(f"Estudo Base: {idioma} ({nivel_global})")
    
    if st.button("✨ Gerar Texto e Áudio", type="primary", width='stretch'):
        with st.spinner("Gerando conteúdo exclusivo..."):
            prompt = f'Crie um texto original em {idioma} nível {nivel_global} (~100 palavras). Retorne JSON: {{"texto": "...", "perguntas": [{{"pergunta": "...", "opcoes": ["A", "B", "C", "D"], "resposta": "A"}}]}}'
            lesson = call_g4f_json(prompt)
            if lesson:
                audio_path = asyncio.run(generate_audio_file(lesson["texto"], get_voice(idioma)))
                st.session_state.study_lesson = lesson
                st.session_state.study_audio = audio_path
                st.session_state.user_data["saved_texts"].append({"idioma": idioma, "texto": lesson["texto"]})
                save_data(st.session_state.user_data)

    if 'study_lesson' in st.session_state:
        st.markdown(f'<div class="premium-card">{st.session_state.study_lesson["texto"]}</div>', unsafe_allow_html=True)
        st.audio(st.session_state.study_audio)
        
        nova_palavra = st.text_input("Salvar palavra nova para os Flashcards:")
        if st.button("Salvar Palavra"):
            p_json = call_g4f_json(f'Traduza "{nova_palavra}" de {idioma} para português. JSON: {{"palavra":"{nova_palavra}", "traducao":"...", "exemplo":"..."}}')
            if p_json:
                st.session_state.user_data["review_words"].append(p_json)
                save_data(st.session_state.user_data)
                st.success(f"Salvo! +5 XP")
                add_xp(5)

# =====================================================================
# 4. MUNDO REAL
# =====================================================================
elif nav == "🌍 Mundo Real":
    st.header("Estude com o que você ama")
    texto_livre = st.text_area("Cole seu texto original aqui (em qualquer idioma):", height=150)
    
    if st.button("🚀 Adaptar e Criar Lição", type="primary", width='stretch'):
        if len(texto_livre) > 20:
            with st.spinner(f"Adaptando texto para {idioma}..."):
                prompt = f'Traduza e adapte o texto a seguir para {idioma} estritamente no nível de fluência {nivel_global}. Crie 3 perguntas de múltipla escolha. Texto: "{texto_livre}". JSON: {{"texto_adaptado": "...", "perguntas": [{{"pergunta": "...", "opcoes": ["A", "B", "C", "D"], "resposta": "A"}}]}}'
                adaptado = call_g4f_json(prompt)
                if adaptado:
                    st.session_state.mundo_real = adaptado
                    st.session_state.user_data["saved_texts"].append({"idioma": idioma, "texto": adaptado["texto_adaptado"]})
                    save_data(st.session_state.user_data)

    if 'mundo_real' in st.session_state:
        st.markdown(f'<div class="premium-card"><b>Texto Adaptado:</b><br><br>{st.session_state.mundo_real["texto_adaptado"]}</div>', unsafe_allow_html=True)
        if st.button("✔️ Finalizar Leitura (50 XP)"):
            add_xp(50)
            st.balloons()

# =====================================================================
# 5. AVALIADOR DE VOZ
# =====================================================================
elif nav == "🎙️ Avaliador de Voz":
    st.header("Teste sua Pronúncia Ativamente")
    
    if 'voice_scenario' not in st.session_state:
        with st.spinner("Gerando cenário..."):
            prompt = f'Crie um cenário curto de conversação em {idioma} (Nível {nivel_global}). Retorne JSON: {{"contexto": "...", "fala_nativa": "..."}}'
            st.session_state.voice_scenario = call_g4f_json(prompt)
            
    scen = st.session_state.voice_scenario
    st.info(f"**Situação:** {scen['contexto']}")
    st.markdown(f"### 🗣️ Nativo: {scen['fala_nativa']}")
    
    audio_bytes = mic_recorder(start_prompt="🔴 Gravar Voz", stop_prompt="⏹️ Parar", key='recorder')
    
    if audio_bytes:
        with st.spinner("Reconhecendo voz..."):
            texto_falado = recognize_audio_from_bytes(audio_bytes['bytes'], idioma)
            if texto_falado:
                st.success(f'**Você disse:** "{texto_falado}"')
                prompt_aval = f'Avalie a gramática e coerência desta resposta falada: "{texto_falado}", para a situação: "{scen["fala_nativa"]}" em {idioma}. JSON: {{"feedback": "...", "sugestao": "..."}}'
                aval = call_g4f_json(prompt_aval)
                if aval:
                    st.markdown(f'<div class="premium-card"><b>Feedback:</b> {aval["feedback"]}<br><br><b>Nativo diria:</b> {aval["sugestao"]}</div>', unsafe_allow_html=True)
                    add_xp(30)
                    st.button("🔄 Próximo Cenário", on_click=lambda: st.session_state.pop('voice_scenario'))
            else:
                st.error("Não entendi o áudio. Fale mais perto do microfone.")

# =====================================================================
# 6. MODO DRIVE
# =====================================================================
elif nav == "🚗 Modo Drive":
    st.header("Modo Direção (Mãos no volante!)")
    
    if st.button("🎧 Iniciar Sessão Hands-Free", type="primary", width='stretch'):
        with st.spinner("Sintetizando podcast..."):
            prompt = f'Crie 5 frases úteis em {idioma} nível {nivel_global}. JSON: {{"frases": [{{"alvo": "frase no idioma", "pt": "tradução"}}]}}'
            frases = call_g4f_json(prompt)
            if frases:
                texto_podcast = "Vamos começar a sessão. "
                for i, f in enumerate(frases["frases"]):
                    texto_podcast += f"Frase {i+1}. Em português: {f['pt']}. . . Agora em {idioma}: . {f['alvo']}. . . . "
                audio_path = asyncio.run(generate_audio_file(texto_podcast, get_voice(idioma)))
                st.session_state.drive_audio = audio_path
                st.session_state.drive_frases = frases["frases"]
                add_xp(20)

    if 'drive_audio' in st.session_state:
        st.markdown('<div class="drive-mode">', unsafe_allow_html=True)
        st.audio(st.session_state.drive_audio, autoplay=True)
        st.markdown('</div>', unsafe_allow_html=True)
        with st.expander("Ver Roteiro (Apenas parado!)"):
            for f in st.session_state.drive_frases:
                st.write(f"🇧🇷 {f['pt']} ➡️ 🎯 {f['alvo']}")

# =====================================================================
# 7. GERADOR DE APOSTILA (FPDF2)
# =====================================================================
elif nav == "📄 Gerar Apostila (PDF)":
    st.header("Exporte seus Estudos")
    
    if st.button("🖨️ Gerar Apostila em PDF", type="primary", width='stretch'):
        db = st.session_state.user_data
        
        if not db["saved_texts"] and not db["review_words"]:
            st.warning("Adicione palavras ou gere textos para ter conteúdo na apostila.")
        else:
            with st.spinner("Diagramando PDF..."):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                pdf.set_font("helvetica", "B", 18)
                pdf.set_text_color(42, 82, 152)
                pdf.cell(0, 10, "LingoTablet Premium - Relatorio de Estudo", ln=True, align='C')
                pdf.ln(5)
                
                pdf.set_font("helvetica", "", 12)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 10, f"XP Total: {db['xp']} | Dias de Ofensiva: {db['streak']}", ln=True, align='C')
                pdf.ln(10)
                
                pdf.set_font("helvetica", "B", 14)
                pdf.set_text_color(30, 60, 114)
                pdf.cell(0, 10, "Seu Dicionario Pessoal", ln=True)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
                for w in db["review_words"]:
                    pdf.set_font("helvetica", "B", 12)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 8, f"{w['palavra']} = {w['traducao']}", ln=True)
                    pdf.set_font("helvetica", "I", 11)
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 6, f"Ex: {w['exemplo']}")
                    pdf.ln(4)
                
                pdf.ln(5)
                pdf.set_font("helvetica", "B", 14)
                pdf.set_text_color(30, 60, 114)
                pdf.cell(0, 10, "Textos Estudados", ln=True)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
                
                for t in db["saved_texts"][-5:]:
                    pdf.set_font("helvetica", "B", 12)
                    pdf.set_text_color(17, 153, 142)
                    pdf.cell(0, 8, f"Idioma: {t['idioma']}", ln=True)
                    pdf.set_font("helvetica", "", 11)
                    pdf.set_text_color(0, 0, 0)
                    texto_limpo = t['texto'].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, texto_limpo)
                    pdf.ln(8)
                
                pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                pdf.output(pdf_file.name)
                
                with open(pdf_file.name, "rb") as file:
                    st.download_button(
                        label="⬇️ Download da Apostila Completa (.PDF)",
                        data=file,
                        file_name=f"LingoTablet_Apostila_{date.today()}.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
                add_xp(15)
