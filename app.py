import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="LEXUS Enterprise", layout="wide", initial_sidebar_state="expanded")

# --- 2. GESTION CLÉ API ---
# Le logiciel va chercher la clé dans le fichier caché .streamlit/secrets.toml
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        # AUTO-DÉTECTION DU MODÈLE (Pour éviter l'erreur 404)
        # On demande à Google quel modèle est disponible pour CE compte
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # On prend le modèle Flash en priorité (rapide et gratuit)
            if "models/gemini-1.5-flash" in available_models:
                CURRENT_MODEL = "models/gemini-1.5-flash"
            elif "models/gemini-pro-vision" in available_models:
                CURRENT_MODEL = "models/gemini-pro-vision"
            else:
                CURRENT_MODEL = available_models[0] # Le premier dispo
            STATUS_MSG = f"Connecté ({CURRENT_MODEL.replace('models/', '')})"
            STATUS_COLOR = "green"
        except:
            STATUS_MSG = "Erreur Modèles"
            STATUS_COLOR = "red"
            CURRENT_MODEL = None
    else:
        STATUS_MSG = "Clé Manquante"
        STATUS_COLOR = "red"
        api_key = None
except:
    STATUS_MSG = "Mode Local (Sans clé)"
    STATUS_COLOR = "orange"
    api_key = None

# --- 3. DESIGN (NOIR & BLEU) ---
st.markdown("""
<style>
    .stApp { background-color: #0F1116; color: #E0E0E0; font-family: 'Arial', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #161920; border-right: 1px solid #2D3139; }
    h1, h2, h3 { color: #FFFFFF; font-weight: 400; }
    div[data-testid="stMetric"] { background-color: #1C2128; border: 1px solid #2D3139; padding: 15px; border-radius: 8px; }
    div[data-testid="stMetricValue"] { color: #3B82F6 !important; font-size: 24px !important; }
    .stButton>button { background-color: #3B82F6; color: white; border: none; border-radius: 6px; font-weight: 600; padding: 10px; width: 100%; }
    .stButton>button:hover { background-color: #2563EB; }
</style>
""", unsafe_allow_html=True)

# --- 4. NAVIGATION ---
if 'view' not in st.session_state: st.session_state.view = 'dashboard'

with st.sidebar:
    st.markdown("### LEXUS ENTERPRISE")
    if st.button("TABLEAU DE BORD"): st.session_state.view = 'dashboard'; st.rerun()
    if st.button("STUDIO IA"): st.session_state.view = 'studio'; st.rerun()
    if st.button("PARAMETRES"): st.session_state.view = 'settings'; st.rerun()
    st.divider()
    st.markdown(f":{STATUS_COLOR}[● {STATUS_MSG}]")

# --- 5. FONCTION ANALYSE ---
def run_analysis(image, prompt):
    if not api_key or not CURRENT_MODEL:
        return "ERREUR : API non connectée."
    try:
        model = genai.GenerativeModel(CURRENT_MODEL)
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Erreur Technique : {str(e)}"

# --- 6. PAGES ---
if st.session_state.view == 'dashboard':
    st.title("Pilotage Commercial")
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Prévisionnel", "1.25M €")
    c2.metric("Dossiers Actifs", "8")
    c3.metric("Performance", "34%")
    st.write("---")
    st.write("### Dossiers Récents")
    cols = st.columns([3, 2, 2])
    cols[0].write("**PROJET**")
    cols[1].write("**BUDGET**")
    cols[2].write("**STATUT**")
    st.markdown("---")
    projects = [("Audit Financier 2026", "12,500 €", "EN COURS"), ("Rénovation Siège", "45,000 €", "ANALYSE")]
    for p in projects:
        c = st.columns([3, 2, 2])
        c[0].write(p[0]); c[1].write(p[1]); c[2].write(p[2])
        st.markdown("---")

elif st.session_state.view == 'studio':
    st.title("Studio d'Analyse")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Source")
        f = st.file_uploader("Image du document", type=['jpg', 'png', 'jpeg'])
        task = st.selectbox("Action", ["Analyse Complète", "Extraction Chiffres", "Synthèse"])
        if f:
            img = Image.open(f)
            st.image(img, caption="Aperçu")
            if st.button("LANCER L'ANALYSE"):
                with st.spinner("Traitement..."):
                    res = run_analysis(img, f"Tu es un expert. Tache : {task}. Analyse ce document.")
                    st.session_state['res'] = res
    with c2:
        st.subheader("Rapport")
        if 'res' in st.session_state:
            st.info("Résultat :")
            st.write(st.session_state['res'])

elif st.session_state.view == 'settings':
    st.title("Configuration")
    st.text_input("Société", value="LEXUS Enterprise")
    st.button("Sauvegarder")