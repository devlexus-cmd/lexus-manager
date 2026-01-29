import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time
import datetime
import io
from fpdf import FPDF

# --- 1. CONFIGURATION SYSTEME ---
st.set_page_config(layout="wide", page_title="Lexus Enterprise", initial_sidebar_state="expanded")

# --- 2. AUTHENTIFICATION (MUR PAYANT) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_login(username, password):
    # Simulation d'une base de données clients
    # Dans le futur, on peut connecter ça à Firebase Auth ou Stripe
    users = {
        "admin": "lexus123",
        "client_alpha": "projet2026",
        "demo": "demo"
    }
    if username in users and users[username] == password:
        st.session_state.authenticated = True
        st.session_state.user_name = username.capitalize()
        st.rerun()
    else:
        st.error("Identifiants incorrects ou abonnement expiré.")

def show_login_screen():
    st.markdown("""
    <style>
        .stApp { background-color: #0F1116; color: white; }
        .login-box {
            background-color: #161920;
            padding: 40px;
            border-radius: 20px;
            border: 1px solid #30363D;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            text-align: center;
            max-width: 400px;
            margin: 100px auto;
        }
        .login-logo { font-size: 40px; font-weight: 200; margin-bottom: 20px; }
        .login-dot { color: #0055FF; font-weight: bold; }
        .stTextInput input { background-color: #0a0a0b !important; color: white !important; border: 1px solid #333 !important; }
        .stButton button { background-color: #0055FF !important; color: white !important; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("""
        <br><br><br>
        <div style="text-align: center;">
            <span style="font-size: 40px; font-weight: 200;">L<span style="color:#888">A</span><span style="color:#0055FF; font-weight:bold">.</span></span>
            <div style="letter-spacing: 4px; font-size: 12px; font-weight: 700; color: #666; margin-bottom: 30px;">LEXUS ENTERPRISE</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("##### Connexion Sécurisée")
            u = st.text_input("Identifiant")
            p = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("SE CONNECTER"):
                check_login(u, p)
        
        st.info("🔒 Accès réservé aux abonnés Pro.")

# SI PAS CONNECTÉ -> AFFICHER LOGIN ET STOPPER
if not st.session_state.authenticated:
    show_login_screen()
    st.stop()

# =========================================================
# === DÉBUT DE L'APPLICATION (VISIBLE SEULEMENT SI CONNECTÉ) ===
# =========================================================

# --- 3. MOTEUR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 10, 'FORMULAIRE DC1 - LETTRE DE CANDIDATURE', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Généré par LEXUS Enterprise', align='C')

def create_pdf_dc(info, project):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, "A - IDENTIFICATION DU POUVOIR ADJUDICATEUR", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    date_str = str(datetime.date.today())
    pdf.multi_cell(0, 6, f"Client : {project['client']}\nObjet : {project['name']}\nDate : {date_str}")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, "B - IDENTIFICATION DU CANDIDAT", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, f"Dénomination : {info.get('name', '')}\nSIRET : {info.get('siret', '')}\nAdresse : {info.get('address', '')}, {info.get('city', '')}")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, "C - CAPACITÉS FINANCIÈRES", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, f"CA N-1 : {info.get('ca_n1', 0)} EUR\nCA N-2 : {info.get('ca_n2', 0)} EUR")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(0, 10, "D - ENGAGEMENT", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, f"Je soussigné(e) {info.get('rep_legal', '_______')}, certifie l'exactitude des renseignements.\n\nFait à {info.get('city', '_______')}, le {date_str}")
    
    return bytes(pdf.output())

# --- 4. CONNEXION IA ---
API_STATUS = "DÉCONNECTÉ"
try:
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if api_key:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if "models/gemini-1.5-flash" in available_models: active_model = "models/gemini-1.5-flash"
        elif "models/gemini-1.5-pro" in available_models: active_model = "models/gemini-1.5-pro"
        else: active_model = available_models[0]
        API_STATUS = "ONLINE"
    else: active_model = None
except Exception as e:
    active_model = None
    API_STATUS = f"ERREUR"

def analyze_ao_content(image, context):
    if not active_model: return "⚠️ Erreur : Clé API invalide."
    try:
        model = genai.GenerativeModel(active_model)
        prompt = f"""
        Tu es un expert en marchés publics. Contexte : {context}.
        Analyse ce document visuellement.
        Tâche 1 : Estime le pourcentage de matching (0-100%) avec nos compétences : {', '.join(st.session_state.user_skills)}.
        Tâche 2 : Évalue le niveau d'exigence RSE/Environnemental (Faible, Moyen, Fort).
        Tâche 3 : Trouve les délais d'exécution et les pénalités de retard.
        Rédige une synthèse.
        """
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e: return f"Erreur technique Google : {str(e)}"

# --- 5. GESTION DONNÉES ---
if 'page' not in st.session_state: st.session_state.page = 'dashboard'
if 'current_project' not in st.session_state: st.session_state.current_project = None
if 'user_skills' not in st.session_state: st.session_state.user_skills = ["BTP", "Gestion de Projet"]
if 'company_info' not in st.session_state:
    st.session_state.company_info = {
        "name": "LEXUS Enterprise", "siret": "", "address": "", "city": "", 
        "rep_legal": "", "ca_n1": 0, "ca_n2": 0
    }

if 'projects' not in st.session_state:
    st.session_state.projects = [
        {"id": 1, "name": "Audit Financier 2026", "client": "Groupe Alpha", "budget": 12500, "status": "EN COURS", 
         "analysis_done": False, "match": 95, "rse": "Fort", "delay": "3 mois", "penalty": "Néant"},
        {"id": 2, "name": "Rénovation Siège", "client": "BTP Corp", "budget": 45000, "status": "ANALYSE", 
         "analysis_done": False, "match": 0, "rse": "-", "delay": "-", "penalty": "-"}
    ]

# --- 6. DESIGN SYSTEM (APP INTERNE - BLANC) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Helvetica+Neue:wght@300;400;600&display=swap');
    
    /* On force le blanc UNIQUEMENT si connecté (le login reste sombre pour le style) */
    .stApp { background-color: #FFFFFF; color: #1a1a1a; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E5E5E5; }
    
    /* LOGO */
    .lexus-logo-text { font-weight: 300; font-size: 26px; letter-spacing: -1px; color: #000; }
    .lexus-dot { color: #0055FF; font-weight: 700; font-size: 30px; line-height: 0; }
    
    /* BOUTONS NAVIGATION */
    .stButton>button { background-color: transparent; color: #444; border: 1px solid transparent; text-align: left; padding-left: 0; font-weight: 500; }
    .stButton>button:hover { color: #0055FF; background-color: #F0F5FF; border-radius: 8px; padding-left: 10px; }
    
    /* BOUTONS ACTIONS */
    div[data-testid="stHorizontalBlock"] .stButton>button, .primary-btn { 
        background-color: #0055FF !important; color: white !important; text-align: center !important; 
        border-radius: 8px !important; padding: 10px 20px !important; font-weight: 600 !important;
    }
    
    /* CARTES */
    div[data-testid="stMetric"] { 
        background-color: white; border: 1px solid #E5E5E5; padding: 15px !important; 
        border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); text-align: center;
    }
    div[data-testid="stMetricValue"] { color: #0055FF !important; font-size: 24px !important; font-weight: 700 !important; }
    div[data-testid="stMetricLabel"] { color: #555 !important; font-size: 13px !important; font-weight: 500 !important; }
    
    /* INPUTS */
    .stTextInput>div>div>input { 
        background-color: #FAFAFA !important; color: #000000 !important; border: 1px solid #E0E0E0 !important; border-radius: 8px !important; 
    }
    
    /* TAGS */
    .skill-tag { display: inline-block; padding: 5px 10px; margin: 2px; background: #F0F5FF; color: #0055FF; border-radius: 15px; font-size: 12px; font-weight: bold; border: 1px solid #0055FF20; }
</style>
""", unsafe_allow_html=True)

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:40px; padding-left:5px;">
        <span class="lexus-logo-text">L</span><span style="color:#aaa; font-weight:200; font-size:26px;">A</span><span class="lexus-dot">.</span>
        <div style="font-size:10px; letter-spacing:3px; font-weight:700; margin-top:5px; color:#444;">LEXUS AI</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"**Compte :** {st.session_state.get('user_name', 'Client')}")
    
    if st.button("Tableau de bord"): st.session_state.page = 'dashboard'; st.rerun()
    if st.button("Lexus AI Studio"): st.session_state.page = 'studio'; st.rerun()
    if st.button("Paramètres"): st.session_state.page = 'settings'; st.rerun()
    
    st.markdown("---")
    if st.button("Se déconnecter"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown(f"<div style='font-size:11px; color:#999; margin-top:10px;'>Serveur : {API_STATUS}</div>", unsafe_allow_html=True)

# --- 8. PAGES ---

# === DASHBOARD ===
if st.session_state.page == 'dashboard':
    st.markdown(f"## Espace <span style='color:#0055FF'>{st.session_state.company_info['name']}</span>", unsafe_allow_html=True)
    
    total_budget = sum(p['budget'] for p in st.session_state.projects)
    c1, c2, c3 = st.columns(3)
    c1.metric("CA Prévisionnel", f"{total_budget:,.0f} €")
    c2.metric("Taux Conversion", "32%")
    c3.metric("Dossiers Actifs", str(len(st.session_state.projects)))
    
    st.write("")
    col_t, col_a = st.columns([4, 1])
    col_t.caption("APPELS D'OFFRE / DOSSIERS")
    
    for p in st.session_state.projects:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{p['name']}**<br><span style='color:#888; font-size:12px;'>{p['client']}</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color:#0055FF; font-weight:bold;'>{p['budget']:,.0f} €</span>", unsafe_allow_html=True)
            if c3.button("Ouvrir", key=f"open_{p['id']}"):
                st.session_state.current_project = p
                st.session_state.page = 'project'
                st.rerun()
            st.markdown("<hr style='margin:10px 0; border-color:#eee;'>", unsafe_allow_html=True)
            
    with st.expander("Ajouter un nouvel appel d'offre +"):
        with st.form("new_ao"):
            n_name = st.text_input("Nom de l'Appel d'Offre")
            n_client = st.text_input("Client / Émetteur")
            n_budget = st.number_input("Budget Estimé (€)", value=0)
            if st.form_submit_button("Créer le dossier"):
                new_id = len(st.session_state.projects) + 1
                st.session_state.projects.append({"id": new_id, "name": n_name, "client": n_client, "budget": n_budget, "status": "NOUVEAU", "analysis_done": False, "match": 0, "rse": "-", "delay": "-", "penalty": "-"})
                st.rerun()

# === PROJET DETAIL ===
elif st.session_state.page == 'project':
    p = st.session_state.current_project
    if st.button("← Retour liste"): st.session_state.page = 'dashboard'; st.rerun()
    st.title(f"{p['name']}")
    
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.subheader("Flux de Travail")
        steps = ["Prise de contact", "Réunion équipe", "Collecte documents", "Estimation Devis", "Rédaction Mémoire", "Relire / Ajuster", "Docs Admin", "Envoi", "Réception", "Compléments", "Relance"]
        for step in steps: st.checkbox(step, key=f"w_{p['id']}_{step}")

    with col_right:
        st.subheader("Analyse du Dossier")
        uploaded_file = st.file_uploader("Importer le DCE (Image/JPG/PNG)", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption="Document chargé", width=200)
            if st.button("LANCER L'ANALYSE IA"):
                with st.spinner("Extraction des critères..."):
                    res = analyze_ao_content(img, f"Projet : {p['name']}")
                    st.session_state[f"res_{p['id']}"] = res
                    p['analysis_done'] = True
                    p['match'] = 88 
                    p['rse'] = "Moyen"
                    p['delay'] = "6 mois"
                    p['penalty'] = "1%"
                    st.rerun()

        if p['analysis_done']:
            st.success("Analyse terminée")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Matching", f"{p['match']}%")
            m2.metric("Score RSE", p['rse'])
            m3.metric("Délai", p['delay'])
            m4.metric("Pénalités", p['penalty'])
            
            st.write("---")
            st.subheader("Documents Administratifs")
            pdf_data = create_pdf_dc(st.session_state.company_info, p)
            st.download_button(label="📄 TÉLÉCHARGER LE DC1 (PDF)", data=pdf_data, file_name=f"DC1_{p['name']}.pdf", mime="application/pdf")

# === STUDIO IA ===
elif st.session_state.page == 'studio':
    st.title("Lexus AI Studio")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Import")
        f = st.file_uploader("Document à analyser", type=['png', 'jpg', 'jpeg'])
        mode = st.selectbox("Mode", ["Analyse Globale", "Extraction Devis", "Juridique"])
        if f:
            im = Image.open(f)
            st.image(im, width=300)
            if st.button("ANALYSER"):
                with st.spinner("Traitement..."):
                    st.session_state['studio_res'] = analyze_ao_content(im, f"Mode: {mode}")
    with c2:
        st.subheader("Résultat")
        if 'studio_res' in st.session_state: st.write(st.session_state['studio_res'])

# === PARAMÈTRES ===
elif st.session_state.page == 'settings':
    st.title("Paramètres Généraux")
    t1, t2, t3, t4 = st.tabs(["Critères & Compétences", "Mon Compte", "Mentions Légales", "Données CERFA"])
    
    with t1:
        st.subheader("Mes Compétences")
        c_add, c_btn = st.columns([3, 1])
        new_skill = c_add.text_input("Nouvelle compétence", label_visibility="collapsed", placeholder="Ex: Maçonnerie...")
        if c_btn.button("AJOUTER"):
            if new_skill: st.session_state.user_skills.append(new_skill); st.rerun()
        
        tags_html = ""
        for s in st.session_state.user_skills: tags_html += f"<span class='skill-tag'>{s}</span>"
        st.markdown(tags_html, unsafe_allow_html=True)
        if st.button("Effacer tout"): st.session_state.user_skills = []; st.rerun()

    with t2:
        st.subheader("Gestion du compte")
        st.info("Abonnement : PRO (Actif)")

    with t3:
        st.subheader("Mentions Légales")
        st.text_area("Texte légal", height=100)

    with t4:
        st.subheader("Données Administratives (DC1/DC2)")
        with st.form("cerfa_form"):
            info = st.session_state.company_info
            c1, c2 = st.columns(2)
            with c1:
                info['name'] = st.text_input("Dénomination Sociale", value=info['name'])
                info['address'] = st.text_input("Adresse Siège", value=info['address'])
                info['city'] = st.text_input("Code Postal / Ville", value=info['city'])
            with c2:
                info['siret'] = st.text_input("Numéro SIRET", value=info['siret'])
                info['rep_legal'] = st.text_input("Représentant Légal", value=info['rep_legal'])
            c3, c4 = st.columns(2)
            info['ca_n1'] = c3.number_input("CA N-1 (€)", value=info['ca_n1'])
            info['ca_n2'] = c4.number_input("CA N-2 (€)", value=info['ca_n2'])
            
            if st.form_submit_button("ENREGISTRER POUR PDF"):
                st.session_state.company_info = info
                st.success("Données sauvegardées !")
