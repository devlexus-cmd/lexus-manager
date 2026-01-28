import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="LEXUS AI | Enterprise Manager",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DESIGN CUSTOM (CSS) ---
# On injecte le style de la maquette pour transformer Streamlit
st.markdown("""
<style>
    /* Couleurs de fond et texte */
    .stApp {
        background-color: #0a0a0b;
        color: #ffffff;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #121214;
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Cartes KPI */
    div[data-testid="metric-container"] {
        background-color: #121214;
        border: 1px solid rgba(255,255,255,0.05);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    /* Boutons */
    .stButton>button {
        background-color: #0055FF;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #0044cc;
        box-shadow: 0 0 15px rgba(0,85,255,0.4);
        transform: translateY(-2px);
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        background-color: #0a0a0b;
        color: white;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Titres */
    h1, h2, h3 {
        font-weight: 300 !important;
    }
    .highlight {
        color: #0055FF;
        font-weight: 700;
    }
    
    /* Zone d'upload */
    [data-testid="stFileUploadDropzone"] {
        background-color: #121214;
        border: 2px dashed rgba(0,85,255,0.3);
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE DE CONNEXION ---
def init_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return models
    except:
        return []

# --- BARRE LATÉRALE (NAVIGATION) ---
with st.sidebar:
    # Logo simulé (LA avec point bleu)
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0;">
        <div style="position: relative; font-size: 28px; font-weight: 300; color: white;">
            L<span style="color: #A0A0A0;">A</span>
            <div style="position: absolute; top: -2px; right: -8px; width: 8px; height: 8px; background-color: #0055FF; rounded-radius: 50%; border-radius: 50%; box-shadow: 0 0 10px #0055FF;"></div>
        </div>
        <div style="font-size: 14px; font-weight: 600; color: white; letter-spacing: 2px; margin-left: 15px; text-transform: uppercase;">Lexus AI</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Système Management v2.5")
    st.divider()
    
    menu = st.radio("NAVIGATION", ["Tableau de Bord", "Lexus AI Studio", "Paramètres"], label_visibility="collapsed")
    
    st.divider()
    api_key = st.text_input("CLÉ API GOOGLE", type="password", placeholder="Votre clé S97M...")
    
    # Auto-détection du modèle
    selected_model = "models/gemini-1.5-flash"
    if api_key:
        available_models = init_gemini(api_key)
        if available_models:
            selected_model = st.selectbox("IA DÉTECTÉE", available_models)
            st.success("Connecté au Cloud")
        else:
            st.error("Clé API Invalide")

# --- FONCTION D'ANALYSE ---
def analyze_document(api_key, model_name, image, task):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = f"Tu es Lexus AI, un assistant expert business. Ta tâche : {task}. Analyse précisément ce document (Excel, Word ou PDF scanné)."
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"Erreur d'analyse : {str(e)}"

# --- PAGE 1 : TABLEAU DE BORD ---
if menu == "Tableau de Bord":
    st.markdown("# Bonjour, <span class='highlight'>Eliot</span>", unsafe_allow_html=True)
    st.write("Voici l'état de vos dossiers stratégiques.")
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Appels d'Offres", "14", "+2 cette semaine")
    c2.metric("Documents Lus", "1,284", "99.8% précision")
    c3.metric("Budget Détecté", "2.4M €", "Opportunités")
    
    st.divider()
    
    st.subheader("Activités Récentes")
    df_data = {
        "Document": ["AO_Siege_Alpha.pdf", "Devis_P3.xlsx", "Contrat_IT.docx", "Audit_RSE.pdf"],
        "Type": ["Appel d'Offre", "Excel / Devis", "Word / Contrat", "Rapport"],
        "Statut": ["✅ Terminé", "✅ Terminé", "⏳ En cours", "✅ Terminé"],
        "Score": ["98%", "100%", "-", "95%"]
    }
    st.table(pd.DataFrame(df_data))

# --- PAGE 2 : LEXUS AI STUDIO ---
elif menu == "Lexus AI Studio":
    st.markdown("# Lexus <span class='highlight'>Studio</span>", unsafe_allow_html=True)
    st.write("Importez vos AO, Excel ou Word pour une extraction instantanée.")
    
    col_input, col_res = st.columns([1, 1])
    
    with col_input:
        st.subheader("1. Import")
        uploaded_file = st.file_uploader("Glissez vos documents ici", type=["jpg", "png", "jpeg"])
        
        task_type = st.selectbox("Action souhaitée", [
            "Analyse complète de l'Appel d'Offre",
            "Extraction des chiffres et tableaux (Excel)",
            "Vérification des clauses de conformité",
            "Synthèse exécutive pour décideurs"
        ])
        
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, use_container_width=True)
            
            if st.button("LANCER L'ANALYSE LEXUS AI 🚀"):
                if not api_key:
                    st.warning("⚠️ Veuillez entrer votre clé API à gauche.")
                else:
                    with st.spinner("L'IA parcourt le document..."):
                        # Petite animation de délai pour le feeling "Premium"
                        time.sleep(1)
                        result = analyze_document(api_key, selected_model, img, task_type)
                        st.session_state['last_result'] = result

    with col_res:
        st.subheader("2. Résultat de l'Intelligence")
        if 'last_result' in st.session_state:
            st.markdown(st.session_state['last_result'])
            st.download_button("Télécharger le rapport", st.session_state['last_result'], "rapport_lexus.txt")
        else:
            st.info("Le rapport détaillé apparaîtra ici après l'analyse.")

# --- PAGE 3 : PARAMÈTRES ---
elif menu == "Paramètres":
    st.markdown("# Paramètres <span class='highlight'>Système</span>", unsafe_allow_html=True)
    
    with st.expander("Profil Entreprise", expanded=True):
        st.text_input("Nom de la société", value="LEXUS Consulting")
        st.selectbox("Secteur principal", ["BTP / Construction", "Audit & Finance", "IT", "Autre"])
        st.text_area("Contexte pour l'IA", placeholder="Décrivez votre activité pour que l'IA soit plus précise...")
        
    with st.expander("Sécurité & API"):
        st.write(f"Modèle actif : {selected_model}")
        st.toggle("Enregistrer les rapports localement", value=True)
        
    if st.button("Sauvegarder les préférences"):
        st.success("Configuration mise à jour.")