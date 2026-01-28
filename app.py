import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="LEXUS Enterprise", page_icon="💎", layout="wide")

# --- DESIGN ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    .stButton>button { background-color: #0044cc; color: white; border-radius: 8px; border: none; padding: 10px; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #003399; }
    h1, h2, h3 { color: #0044cc; }
    div.stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("💎 LEXUS MANAGER")
    st.caption("Version Production (Auto-Détection)")
    
    api_key = st.text_input("Clé API Google", type="password", placeholder="Collez votre clé ...S97M")
    
    # --- AUTO-DETECTION DES MODÈLES DISPONIBLES ---
    available_models = []
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # On demande à Google ce qui est dispo pour CETTE clé
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except Exception as e:
            st.error(f"Clé invalide : {e}")

    # Sélecteur de modèle (pour éviter l'erreur 404)
    if available_models:
        selected_model = st.selectbox("Modèle IA détecté", available_models, index=0)
        st.success(f"✅ Connecté à {selected_model}")
    else:
        if api_key:
            st.warning("⚠️ Aucun modèle trouvé. Vérifiez que l'API est activée sur Google Cloud.")
        selected_model = "models/gemini-1.5-flash" # Valeur par défaut
    
    menu = st.radio("Navigation", ["Tableau de Bord", "Lexus AI Studio", "Paramètres"])

# --- FONCTION IA RÉELLE ---
def analyze_real(api_key, model_name, image, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"❌ ERREUR TECHNIQUE :\n{str(e)}\n\n👉 Conseil : Essayez de changer de modèle dans le menu de gauche."

# --- PAGE 1 : DASHBOARD ---
if menu == "Tableau de Bord":
    st.title("📊 Pilotage Commercial")
    c1, c2, c3 = st.columns(3)
    c1.metric("Chiffre d'Affaires", "1,250,000 €", "+12%")
    c2.metric("Dossiers en cours", "8", "Actifs")
    c3.metric("Taux de Conversion", "32%", "+4%")
    st.divider()
    st.subheader("Derniers Appels d'Offres")
    df = pd.DataFrame({
        "Projet": ["Audit Financier 2024", "Siège Social BTP", "Conseil IT Stratégique", "Audit RSE Global"],
        "Client": ["Groupe Alpha", "BTP Corp", "Tech Solutions", "Green Energy"],
        "Budget": ["12,500 €", "45,000 €", "8,200 €", "22,000 €"],
        "Statut": ["✅ En cours", "⏳ Analyse", "❌ Rejeté", "✅ En cours"]
    })
    st.dataframe(df, use_container_width=True)

# --- PAGE 2 : IA STUDIO ---
elif menu == "Lexus AI Studio":
    st.title("✨ Intelligence Artificielle (RÉEL)")
    
    col_g, col_d = st.columns([1, 1])
    
    with col_g:
        st.subheader("1. Import")
        uploaded_file = st.file_uploader("Image du document", type=["jpg", "png", "jpeg"])
        task = st.selectbox("Action", ["Analyse complète", "Extraction des montants", "Synthèse", "Rédaction email"])
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, width=300)
            
            if st.button("LANCER L'ANALYSE (VRAIE) 🚀"):
                if not api_key:
                    st.error("Il manque la Clé API !")
                else:
                    with st.spinner(f"Interrogation de {selected_model}..."):
                        res = analyze_real(api_key, selected_model, image, f"Tu es un expert business. Tache : {task}. Analyse ce document visuellement.")
                        st.session_state['resultat_reel'] = res

    with col_d:
        st.subheader("2. Résultat")
        if 'resultat_reel' in st.session_state:
            st.success("Réponse reçue de Google")
            st.text_area("Rapport", st.session_state['resultat_reel'], height=500)

# --- PAGE 3 : PARAMÈTRES ---
elif menu == "Paramètres":
    st.title("⚙️ Configuration")
    st.text_input("Société", value="LEXUS Enterprise")