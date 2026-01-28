import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time
import datetime

# --- 1. CONFIGURATION SYSTÈME ---
st.set_page_config(
    page_title="LEXUS AI | Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GESTION D'ÉTAT (MÉMOIRE DU LOGICIEL) ---
# C'est ici qu'on stocke les données pour qu'elles ne disparaissent pas quand on clique.
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'projects' not in st.session_state:
    # Données simulées initiales
    st.session_state.projects = [
        {"id": 1, "name": "Audit Financier 2026", "client": "Groupe Alpha", "budget": "12,500 €", "status": "En cours", "match": 95, "workflow_progress": 0.2},
        {"id": 2, "name": "Rénovation Siège Social", "client": "BTP Corp", "budget": "45,000 €", "status": "Analyse", "match": 85, "workflow_progress": 0.0},
        {"id": 3, "name": "Stratégie IT Global", "client": "Tech Solutions", "budget": "8,200 €", "status": "Rejeté", "match": 70, "workflow_progress": 1.0},
    ]

# --- 3. STYLE CSS PREMIUM (NOIR PROFOND & BLEU ELECTRIQUE) ---
st.markdown("""
<style>
    /* RESET & BASE */
    .stApp { background-color: #0a0a0b; color: #ffffff; font-family: 'Helvetica Neue', sans-serif; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #111114 !important; border-right: 1px solid rgba(255,255,255,0.05); }
    
    /* CARTES & CONTENEURS */
    .project-card {
        background-color: #16161a;
        border: 1px solid rgba(255,255,255,0.05);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        transition: all 0.2s ease;
    }
    .project-card:hover { border-color: #0055FF; transform: translateY(-2px); }
    
    /* METRICS */
    div[data-testid="stMetric"] {
        background-color: #16161a;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    div[data-testid="stMetricValue"] { color: #0055FF !important; }
    
    /* BOUTONS */
    .stButton>button {
        background-color: #0055FF;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        transition: 0.3s;
        width: 100%;
    }
    .stButton>button:hover { background-color: #0044cc; box-shadow: 0 0 15px rgba(0,85,255,0.4); }
    
    /* BOUTON SECONDAIRE (Gris) */
    .secondary-button>button { background-color: #2a2a30; }
    
    /* INPUTS */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #16161a !important; color: white !important; border: 1px solid #333 !important;
    }
    
    /* NAVIGATION STEPS */
    .step-container {
        display: flex; align-items: center; padding: 10px; 
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .step-title { font-weight: bold; font-size: 14px; margin-left: 10px; }
    .step-desc { font-size: 12px; color: #888; margin-left: 10px; }
    
    /* BADGES */
    .badge-blue { background-color: rgba(0,85,255,0.15); color: #0055FF; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .badge-green { background-color: rgba(0,255,128,0.15); color: #00FF80; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. FONCTIONS LOGIQUES ---
def navigate_to(page, project=None):
    st.session_state.page = page
    if project:
        st.session_state.selected_project = project
    st.rerun()

def detect_models(api_key):
    try:
        genai.configure(api_key=api_key)
        return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except: return []

# --- 5. SIDEBAR (LOGO & MENU) ---
with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px;">
            <div style="position:relative; font-size:32px; font-weight:200;">L<span style="color:#888;">A</span>
            <div style="position:absolute; top:2px; right:-8px; width:8px; height:8px; background:#0055FF; border-radius:50%; box-shadow:0 0 15px #0055FF;"></div></div>
            <div style="font-weight:700; letter-spacing:2px; font-size:14px; margin-left:15px;">LEXUS AI</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Menu de navigation principal
    if st.button("📊  Tableau de Bord", use_container_width=True): navigate_to('dashboard')
    if st.button("✨  Lexus AI Studio", use_container_width=True): navigate_to('ai_studio')
    if st.button("⚙️  Paramètres", use_container_width=True): navigate_to('settings')
    
    st.divider()
    
    # Configuration API
    api_key_input = st.text_input("CLÉ API GOOGLE", type="password", placeholder="Saisir votre clé...")
    
    current_model = "models/gemini-1.5-flash"
    if api_key_input:
        available_models = detect_models(api_key_input)
        if available_models:
            # Auto-sélection intelligente
            idx = 0
            if "models/gemini-2.5-pro" in available_models: idx = available_models.index("models/gemini-2.5-pro")
            elif "models/gemini-1.5-flash" in available_models: idx = available_models.index("models/gemini-1.5-flash")
            
            current_model = st.selectbox("IA CONNECTÉE", available_models, index=idx)
            st.success("Système en ligne")
        else:
            st.error("Erreur Clé API")

# --- 6. ROUTEUR DE PAGES ---

# ==========================================
# PAGE : TABLEAU DE BORD (DASHBOARD)
# ==========================================
if st.session_state.page == 'dashboard':
    st.markdown("<h1 style='font-weight:200; margin-bottom:0;'>Pilotage <span style='color:#0055FF; font-weight:700;'>Global</span></h1>", unsafe_allow_html=True)
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA Prévisionnel", "1.2M €", "+12%")
    c2.metric("Dossiers Actifs", str(len(st.session_state.projects)), "+2")
    c3.metric("Taux Succès", "32%", "Stable")
    c4.metric("Actions à faire", "5", "Urgent")
    
    st.write("") # Spacer
    
    # Section Projets
    col_title, col_btn = st.columns([4, 1])
    with col_title: st.subheader("Vos Dossiers en cours")
    with col_btn: 
        if st.button("➕ Nouveau Dossier"):
            st.toast("Module de création ouvert (Simulation)")
    
    # Affichage des cartes projets (Liste interactive)
    for project in st.session_state.projects:
        # On crée une "Card" visuelle
        with st.container():
            st.markdown(f"""
            <div class="project-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-size:18px; font-weight:bold;">{project['name']}</div>
                        <div style="color:#888; font-size:14px;">{project['client']} • <span style="color:#0055FF;">{project['budget']}</span></div>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge-blue">{project['status']}</span>
                        <span class="badge-green">{project['match']}% Match</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Le bouton "Détails" invisible qui couvre la carte (hack Streamlit)
            # Ici on utilise un vrai bouton en dessous pour l'interaction
            c_space, c_btn = st.columns([5, 1])
            with c_btn:
                if st.button("Ouvrir ➔", key=f"btn_{project['id']}"):
                    navigate_to('project_detail', project)

# ==========================================
# PAGE : DÉTAILS PROJET (LE WORKFLOW)
# ==========================================
elif st.session_state.page == 'project_detail':
    proj = st.session_state.selected_project
    
    # Fil d'ariane
    if st.button("← Retour au Tableau de bord", type="secondary"): navigate_to('dashboard')
    
    st.markdown(f"<h1 style='font-weight:700;'>{proj['name']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:#888; font-weight:300;'>Client : {proj['client']} | Budget : <span style='color:#0055FF;'>{proj['budget']}</span></h3>", unsafe_allow_html=True)
    
    st.divider()
    
    # Layout : Workflow à gauche, IA et Actions à droite
    col_work, col_actions = st.columns([2, 1])
    
    with col_work:
        st.subheader("Workflow Opérationnel")
        
        # Liste des 11 étapes demandées
        steps = [
            ("1. Prise de contact", "Repérer la personne clé dans les docs"),
            ("2. Réunir l'équipe", "Lister compétences, SIRET, CV, Portfolio"),
            ("3. Collecter les docs", "Lister infos manquantes, questions à poser"),
            ("4. Estimer 1er devis", "Méthodo, chiffrage jours/km"),
            ("5. Écrire le mémoire", "Note méthodologique, RSE, Vision"),
            ("6. Relire / Ajuster", "Aller-retour sur l'estimation"),
            ("7. Docs Administratifs", "DC1, DC2, DPGF, BPU, AE"),
            ("8. Synthèse & Envoi", "Vérifier complétude et envoyer"),
            ("9. Réception", "Confirmer la bonne réception"),
            ("10. Compléter", "Si besoin, rajouter pièces"),
            ("11. Relancer", "Suivre pour la réponse")
        ]
        
        for i, (title, desc) in enumerate(steps):
            chk = st.checkbox(f"**{title}**", key=f"step_{i}", help=desc)
            if chk:
                st.caption(f"✅ *{desc}*")
            else:
                st.caption(f"⚪️ {desc}")
            st.divider()

    with col_actions:
        st.subheader("Intelligence Artificielle")
        st.info("Utilisez Lexus AI pour accélérer ce dossier.")
        
        with st.expander("📄 Analyser l'Appel d'Offre", expanded=True):
            uploaded_ao = st.file_uploader("Déposer le PDF/Image du DCE", type=['jpg', 'png', 'pdf'])
            if uploaded_ao and st.button("Analyser les critères"):
                with st.spinner("Lecture des contraintes..."):
                    time.sleep(2)
                    st.success("Critères extraits : RSE (20%), Prix (40%), Tech (40%)")
        
        with st.expander("💰 Générer le Devis"):
            st.write("Basé sur votre taux journalier (450€)")
            if st.button("Calculer l'estimation"):
                st.success("Estimation : 12.5 jours = 5,625€ HT")
        
        with st.expander("📝 Rédiger le Mémoire"):
            st.write("Génération du plan type")
            if st.button("Générer le plan"):
                st.success("Plan généré dans l'onglet Documents")

# ==========================================
# PAGE : LEXUS AI STUDIO (OUTILS)
# ==========================================
elif st.session_state.page == 'ai_studio':
    st.markdown("<h1 style='font-weight:200;'>Lexus <span style='color:#0055FF; font-weight:700;'>Studio</span></h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📤 Import & Analyse", "💶 Générateur Devis", "📧 Assistant Mail"])
    
    with tab1:
        c1, c2 = st.columns([1,1])
        with c1:
            st.subheader("Zone d'Analyse")
            f = st.file_uploader("Déposer un document (Image)", type=['jpg', 'png', 'jpeg'])
            task = st.selectbox("Objectif", ["Synthèse", "Extraction Données", "Conformité"])
            if f and st.button("Lancer l'analyse 🚀"):
                if not api_key_input:
                    st.error("Clé API manquante")
                else:
                    with st.spinner("Analyse par Gemini..."):
                        try:
                            genai.configure(api_key=api_key_input)
                            model = genai.GenerativeModel(current_model)
                            img = Image.open(f)
                            res = model.generate_content([f"Agis comme un expert. Tache : {task}. Analyse cette image.", img])
                            st.session_state['ai_res_studio'] = res.text
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        with c2:
            st.subheader("Résultat")
            if 'ai_res_studio' in st.session_state:
                st.info("Terminé")
                st.markdown(st.session_state['ai_res_studio'])
    
    with tab2:
        st.header("Outil de Chiffrage")
        st.write("Cet outil calculera automatiquement votre devis basé sur vos paramètres.")
        # Ici on pourrait mettre les formulaires de calcul
        
    with tab3:
        st.header("Rédaction de Mails")
        st.text_area("Contexte du mail", placeholder="Ex: Relance client pour le devis envoyé mardi...")
        st.button("Générer le brouillon")

# ==========================================
# PAGE : PARAMÈTRES
# ==========================================
elif st.session_state.page == 'settings':
    st.markdown("<h1 style='font-weight:200;'>Configuration <span style='color:#0055FF; font-weight:700;'>Système</span></h1>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Entreprise", "Documents Types"])
    
    with t1:
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Nom Société", value="LEXUS Enterprise")
            st.text_input("SIRET")
            st.text_input("Dirigeant", placeholder="Nom Prénom")
        with c2:
            st.number_input("Taux Journalier (€)", value=450)
            st.text_area("Compétences Clés (séparées par des virgules)", value="Audit, BTP, Finance, Gestion de projet")
            
    with t2:
        st.subheader("Modèles Administratifs")
        st.text_area("Conditions Générales de Vente (CGV)", height=200, placeholder="Copiez vos CGV ici...")
        st.text_area("Mentions Légales DC1/DC2", height=150)
    
    st.write("")
    if st.button("Sauvegarder tout"):
        st.success("Paramètres enregistrés dans la base locale.")