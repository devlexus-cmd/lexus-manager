import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time
import io
import datetime 
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Lexus Enterprise", initial_sidebar_state="collapsed")

# --- 2. CONFIGURATION ABONNEMENTS (STRIPE) ---
# C'est ici que la logique financière est stockée
PLANS = {
    "GRATUIT": {
        "limit": 3, 
        "price": "0€", 
        "label": "Découverte",
        "link": None
    },
    "PRO": {
        "limit": 30, 
        "price": "15€", 
        "label": "Professionnel",
        "link": "https://buy.stripe.com/3cIdR22u00uL2tB5BH08g00" # REMPLACER PAR VOTRE LIEN STRIPE
    },
    "ULTRA": {
        "limit": 999999, 
        "price": "55€", 
        "label": "Illimité",
        "link": "https://buy.stripe.com/votre_lien_ultra_ici" # REMPLACER PAR VOTRE LIEN STRIPE
    }
}

# --- 3. GESTION DE L'ÉTAT ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'auth_view' not in st.session_state: st.session_state.auth_view = 'landing'
if 'user_name' not in st.session_state: st.session_state.user_name = "Client"
if 'page' not in st.session_state: st.session_state.page = 'dashboard'
if 'current_project' not in st.session_state: st.session_state.current_project = None
if 'company_info' not in st.session_state: st.session_state.company_info = {"name": "LEXUS Enterprise", "siret": "", "address": "", "city": "", "rep_legal": "", "ca_n1": 0, "ca_n2": 0}

# Variables d'abonnement
if 'subscription_plan' not in st.session_state: st.session_state.subscription_plan = "GRATUIT"
if 'credits_used' not in st.session_state: st.session_state.credits_used = 1

# Données persistantes
if 'projects' not in st.session_state:
    st.session_state.projects = []
if 'user_criteria' not in st.session_state:
    st.session_state.user_criteria = {
        "skills": ["BTP", "Gestion"],
        "min_daily_rate": 450,
        "max_distance": 50,
        "certifications": [],
        "min_turnover_required": 0,
        "max_penalties": 5
    }
if 'user_skills' not in st.session_state: 
    st.session_state.user_skills = st.session_state.user_criteria['skills']

# --- 4. CSS GLOBAL (LANDING V10.5 RESTAURÉE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* BASE */
    .stApp { background-color: #FFFFFF; color: #111111; font-family: 'Inter', sans-serif; }
    
    /* CACHER ÉLÉMENTS PARASITES */
    .stApp > header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* LOGO LEXUS */
    .lexus-logo-text { font-weight: 300; font-size: 24px; letter-spacing: -1px; color: #000 !important; }
    .lexus-dot { color: #0055FF; font-weight: 700; font-size: 28px; line-height: 0; }
    
    /* LANDING PAGE STYLES (RESTAURÉS) */
    .hero-title { 
        font-size: 56px; font-weight: 800; line-height: 1.1; margin-bottom: 20px; color: #000; letter-spacing: -2px; text-align: center;
    }
    .hero-subtitle { 
        font-size: 20px; font-weight: 300; color: #666; margin-bottom: 40px; text-align: center; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5;
    }
    
    /* FEATURES GRID (Clean sans emoji) */
    .feature-card {
        padding: 40px 30px; border: 1px solid #eee; border-radius: 12px; text-align: center; transition: 0.3s;
        height: 100%; display: flex; flex-direction: column; align-items: center;
    }
    .feature-card:hover { border-color: #0055FF; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
    .feature-icon svg { width: 32px; height: 32px; stroke: #0055FF; margin-bottom: 20px; }
    .feature-title { font-weight: 600; font-size: 18px; margin-bottom: 10px; color: #000; }
    .feature-desc { font-size: 14px; color: #666; line-height: 1.5; }

    /* BOUTONS NAVIGATION APP */
    .stButton>button { background-color: transparent; color: #444; border: 1px solid transparent; text-align: left; padding-left: 0; font-weight: 500; }
    .stButton>button:hover { color: #0055FF; background-color: #F0F5FF; border-radius: 8px; padding-left: 10px; }
    
    /* BOUTONS ACTIONS BLEUS */
    div[data-testid="stHorizontalBlock"] .stButton>button, 
    .primary-btn, 
    .stFormSubmitButton>button, 
    div.stButton > button:first-child { 
        background-color: #0055FF !important; color: white !important; text-align: center !important; 
        border-radius: 8px !important; padding: 12px 24px !important; font-weight: 600 !important; border: none !important;
        width: 100%; box-shadow: 0 10px 20px rgba(0,85,255,0.2) !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton>button:hover, .stFormSubmitButton>button:hover {
        background-color: #0044cc !important; transform: translateY(-2px);
    }
    
    /* Exception sidebar */
    section[data-testid="stSidebar"] .stButton>button {
        background-color: transparent !important; color: #444 !important; box-shadow: none !important; text-align: left !important;
    }
    section[data-testid="stSidebar"] .stButton>button:hover {
        background-color: #F0F5FF !important; color: #0055FF !important;
    }

    /* CARTES STATS */
    .kpi-card {
        background-color: white; border: 1px solid #E5E5E5; padding: 20px; 
        border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        text-align: center; display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 110px;
    }
    .kpi-label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 8px; font-weight: 600; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #0055FF; }
    .kpi-sub { font-size: 11px; color: #888; margin-top: 5px; }
    
    /* CARTE ABONNEMENT */
    .sub-card {
        background-color: #1a1a1a; color: white; padding: 25px; border-radius: 15px; 
        border: 1px solid #333; position: relative; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px;
    }
    .sub-name { color: #0055FF; font-size: 14px; font-weight: 800; letter-spacing: 2px; margin-bottom: 10px; }
    .sub-price { font-size: 32px; font-weight: 700; margin-bottom: 5px; color: white; }
    .sub-period { font-size: 14px; color: #888; font-weight: 400; }
    .sub-badge {
        background-color: #00C853; color: white; padding: 4px 10px; 
        border-radius: 20px; font-size: 10px; font-weight: bold;
        position: absolute; top: 20px; right: 20px;
    }
    
    /* INPUTS */
    .stTextInput>div>div>input { background-color: #FAFAFA !important; color: #000; border: 1px solid #E0E0E0; border-radius: 8px; }
    
    /* TAGS */
    .skill-tag { display: inline-block; padding: 5px 10px; margin: 2px; background: #F0F5FF; color: #0055FF; border-radius: 15px; font-size: 12px; font-weight: bold; border: 1px solid #0055FF20; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# === PARTIE 1 : LANDING PAGE & AUTHENTIFICATION (V10.5) ===
# =========================================================

def login_screen():
    c1, c2 = st.columns([1, 6])
    with c1:
        st.markdown("<div style='padding-top:10px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
    with c2:
        sc1, sc2, sc3 = st.columns([5, 0.5, 1.5])
        if sc3.button("Se connecter", key="btn_login_home"): st.session_state.auth_view = 'login'; st.rerun()

    st.write(""); st.write(""); st.write(""); st.write("")
    st.markdown("<div class='hero-title'>L'Intelligence Artificielle pour<br><span style='color:#0055FF'>vos marchés publics.</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Centralisez vos appels d'offres. Analysez vos documents en un clic.<br>Générez vos dossiers administratifs sans erreur.</div>", unsafe_allow_html=True)
    
    c_cta1, c_cta2, c_cta3 = st.columns([1, 1, 1])
    with c_cta2:
        with st.form("hero_cta"):
            if st.form_submit_button("CRÉER UN COMPTE GRATUIT"):
                st.session_state.auth_view = 'signup'
                st.rerun()
        st.markdown("<div style='text-align:center; font-size:12px; color:#888; margin-top:10px;'>Accès immédiat • Paiement à la consommation IA</div>", unsafe_allow_html=True)

    st.write(""); st.write(""); st.write("")
    
    # FEATURES GRID
    c_f1, c_f2, c_f3 = st.columns(3)
    with c_f1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
            </div>
            <div class="feature-title">Analyse Sémantique</div>
            <div class="feature-desc">Notre IA lit et comprend vos cahiers des charges. Elle extrait instantanément les critères et délais.</div>
        </div>
        """, unsafe_allow_html=True)
    with c_f2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
            </div>
            <div class="feature-title">Gestion Administrative</div>
            <div class="feature-desc">Fini la saisie manuelle. Lexus pré-remplit vos DC1, DC2 et documents de conformité.</div>
        </div>
        """, unsafe_allow_html=True)
    with c_f3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>
            </div>
            <div class="feature-title">Pilotage Financier</div>
            <div class="feature-desc">Un tableau de bord clair pour suivre vos taux de succès et votre CA prévisionnel.</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    st.markdown("<hr style='border:0; border-top:1px solid #eee; margin: 50px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#888; font-size:12px;'>© 2026 LEXUS Enterprise.</div>", unsafe_allow_html=True)

def auth_form(mode):
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; margin-bottom:20px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; margin-bottom:30px;'>{mode}</h3>", unsafe_allow_html=True)
        with st.form("auth"):
            st.text_input("Email professionnel")
            st.text_input("Mot de passe", type="password")
            if mode == "Créer un compte": st.text_input("Nom de l'entreprise")
            btn_text = "SE CONNECTER" if mode == "Se connecter" else "S'INSCRIRE"
            if st.form_submit_button(btn_text): 
                st.session_state.authenticated = True
                st.rerun()
        if st.button("← Retour"): st.session_state.auth_view = 'landing'; st.rerun()

if not st.session_state.authenticated:
    if st.session_state.auth_view == 'landing': login_screen()
    elif st.session_state.auth_view == 'login': auth_form("Se connecter")
    elif st.session_state.auth_view == 'signup': auth_form("Créer un compte")
    st.stop()

# =========================================================
# === PARTIE 2 : LE LOGICIEL MÉTIER ===
# =========================================================

# --- MOTEUR PDF ---
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
    pdf.set_fill_color(245, 245, 245)
    date_str = str(datetime.date.today())
    sections = [
        ("A - POUVOIR ADJUDICATEUR", f"Client : {project['client']}\nObjet : {project['name']}\nDate : {date_str}"),
        ("B - CANDIDAT", f"Société : {info.get('name', '')}\nSIRET : {info.get('siret', '')}\nAdresse : {info.get('address', '')}"),
        ("C - CAPACITÉS", f"CA N-1 : {info.get('ca_n1', 0)} €\nCA N-2 : {info.get('ca_n2', 0)} €"),
        ("D - ENGAGEMENT", f"Signé par {info.get('rep_legal', '')}.\nFait à {info.get('city', '')}, le {date_str}")
    ]
    for title, content in sections:
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, content)
        pdf.ln(5)
    return bytes(pdf.output())

# --- CONNEXION IA ---
API_STATUS = "OFFLINE"
try:
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if api_key:
        genai.configure(api_key=api_key)
        m = [model.name for model in genai.list_models() if 'generateContent' in model.supported_generation_methods]
        if "models/gemini-1.5-flash" in m: active_model = "models/gemini-1.5-flash"
        elif "models/gemini-1.5-pro" in m: active_model = "models/gemini-1.5-pro"
        else: active_model = m[0] if m else None
        API_STATUS = "ONLINE"
    else: active_model = None
except: active_model = None

def analyze(image, prompt):
    # CONTROLE ABONNEMENT
    plan = PLANS[st.session_state.subscription_plan]
    if st.session_state.credits_used >= plan['limit']:
        return f"⚠️ LIMITE ATTEINTE : Vous avez utilisé vos {plan['limit']} analyses. Passez à l'offre supérieure."

    if not active_model: return "⚠️ Clé API invalide."
    try:
        model = genai.GenerativeModel(active_model)
        res = model.generate_content([prompt, image]).text
        st.session_state.credits_used += 1 # Débit
        return res
    except Exception as e: return f"Erreur : {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""<div style='margin-bottom:40px; padding-left:5px;'><span class='lexus-logo-text'>L</span><span style='color:#aaa; font-weight:200; font-size:26px;'>A</span><span class='lexus-dot'>.</span><div style='font-size:10px; letter-spacing:3px; font-weight:700; margin-top:5px; color:#444;'>LEXUS AI</div></div>""", unsafe_allow_html=True)
    if st.button("Tableau de bord"): st.session_state.page = 'dashboard'; st.rerun()
    if st.button("Lexus AI Studio"): st.session_state.page = 'studio'; st.rerun()
    if st.button("Paramètres"): st.session_state.page = 'settings'; st.rerun()
    st.markdown("---")
    if st.button("Déconnexion"): st.session_state.authenticated = False; st.session_state.auth_view = 'landing'; st.rerun()
    st.markdown(f"<div style='font-size:11px; color:#999; margin-top:10px;'>Serveur : {API_STATUS}</div>", unsafe_allow_html=True)

# --- PAGES ---

# DASHBOARD
if st.session_state.page == 'dashboard':
    st.markdown(f"## Espace <span style='color:#0055FF'>{st.session_state.company_info['name']}</span>", unsafe_allow_html=True)
    total = sum(p['budget'] for p in st.session_state.projects)
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">CA PRÉVISIONNEL</div><div class="kpi-value">{total:,.0f} €</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">TAUX DE SUCCÈS</div><div class="kpi-value">32%</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">DOSSIERS ACTIFS</div><div class="kpi-value">{len(st.session_state.projects)}</div></div>""", unsafe_allow_html=True)
    
    st.write(""); st.write(""); st.caption("APPELS D'OFFRE / DOSSIERS")
    
    if not st.session_state.projects:
        st.info("Aucun dossier en cours. Créez votre premier projet ci-dessous.")
    else:
        for p in st.session_state.projects:
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{p['name']}**<br><span style='color:#888; font-size:12px;'>{p['client']}</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:#0055FF; font-weight:bold;'>{p['budget']:,.0f} €</span>", unsafe_allow_html=True)
                if c3.button("Ouvrir", key=f"open_{p['id']}"): st.session_state.current_project = p; st.session_state.page = 'project'; st.rerun()
                st.markdown("<hr style='margin:10px 0; border-color:#eee;'>", unsafe_allow_html=True)
            
    with st.expander("Ajouter un nouvel appel d'offre +"):
        with st.form("new_ao"):
            n_name = st.text_input("Nom"); n_client = st.text_input("Client"); n_budget = st.number_input("Budget", value=0)
            if st.form_submit_button("Créer"):
                st.session_state.projects.append({"id": len(st.session_state.projects)+1, "name": n_name, "client": n_client, "budget": n_budget, "status": "NOUVEAU", "analysis_done": False, "match": 0, "rse": "-", "delay": "-", "penalty": "-"})
                st.rerun()

# DETAIL PROJET
elif st.session_state.page == 'project':
    p = st.session_state.current_project
    if st.button("← Retour liste"): st.session_state.page = 'dashboard'; st.rerun()
    st.title(f"{p['name']}")
    c_left, c_right = st.columns([1, 1], gap="large")
    with c_left:
        st.subheader("Flux de Travail")
        steps = ["Prise de contact", "Réunion équipe", "Collecte documents", "Estimation Devis", "Rédaction Mémoire", "Relire", "Docs Admin", "Envoi", "Réception", "Compléments", "Relance"]
        for step in steps: st.checkbox(step, key=f"w_{p['id']}_{step}")
    with c_right:
        st.subheader("Analyse du Dossier")
        uploaded_file = st.file_uploader("Importer le DCE (Image/JPG/PNG)", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            img = Image.open(uploaded_file); st.image(img, caption="Document chargé", width=200)
            if st.button("LANCER L'ANALYSE IA"):
                with st.spinner("Extraction..."):
                    # CRITERES UTILISATEUR ENVOYÉS AU PROMPT
                    criteria_text = f"Compétences: {', '.join(st.session_state.user_criteria['skills'])}. CA Min requis: {st.session_state.user_criteria['min_turnover_required']}€. Pénalités Max: {st.session_state.user_criteria['max_penalties']}%."
                    res = analyze(img, f"Projet : {p['name']}. Contexte : {criteria_text}. Extrais Matching, RSE, Délai, Pénalités.")
                    st.session_state[f"res_{p['id']}"] = res; p['analysis_done'] = True; p['match'], p['rse'], p['delay'], p['penalty'] = 88, "Moyen", "6 mois", "1%"; st.rerun()
        if p['analysis_done']:
            st.success("Analyse terminée")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>MATCHING</div><div class='kpi-value'>{p['match']}%</div></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>RSE</div><div class='kpi-value'>{p['rse']}</div></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>DÉLAI</div><div class='kpi-value'>{p['delay']}</div></div>", unsafe_allow_html=True)
            with c4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>PÉNALITÉS</div><div class='kpi-value'>{p['penalty']}</div></div>", unsafe_allow_html=True)
            with st.expander("Voir le Compte Rendu Détaillé", expanded=True):
                 if f"res_{p['id']}" in st.session_state: st.write(st.session_state[f"res_{p['id']}"])
            st.write("---")
            st.subheader("Administratif")
            pdf_data = create_pdf_dc(st.session_state.company_info, p)
            st.download_button(label="📄 TÉLÉCHARGER LE DC1 (PDF)", data=pdf_data, file_name=f"DC1_{p['name']}.pdf", mime="application/pdf")

# STUDIO IA
elif st.session_state.page == 'studio':
    st.title("Lexus AI Studio")
    c1, c2 = st.columns(2)
    with c1:
        f = st.file_uploader("Document", type=['png', 'jpg', 'jpeg'])
        mode = st.selectbox("Mode", ["Globale", "Devis", "Juridique"])
        if f:
            im = Image.open(f); st.image(im, width=300)
            if st.button("ANALYSER"):
                with st.spinner("Traitement..."): st.session_state['studio_res'] = analyze(im, f"Mode: {mode}")
    with c2:
        if 'studio_res' in st.session_state: st.write(st.session_state['studio_res'])

# PARAMETRES (AVEC GESTION ABONNEMENT)
elif st.session_state.page == 'settings':
    st.title("Paramètres Généraux")
    t1, t2, t3, t4 = st.tabs(["Critères & Compétences", "Mon Compte & Abo", "Mentions Légales", "Données CERFA"])
    
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

        st.divider()
        st.subheader("Critères Financiers")
        st.number_input("Taux Journalier Minimum (€)", value=st.session_state.user_criteria['min_daily_rate'])
        st.slider("Pénalités max acceptées (%)", 0, 20, 5)
        st.number_input("Chiffre d'Affaires Minimum requis par le marché", value=0)

    # 2. MON COMPTE & ABO (3 OFFRES STRIPE)
    with t2:
        st.subheader("Mon Abonnement")
        
        # Affichage des 3 plans
        c_gratuit, c_pro, c_ultra = st.columns(3)
        
        def show_plan(key, plan_data, color):
            is_active = st.session_state.subscription_plan == key
            border = f"border: 2px solid {color};" if is_active else "border: 1px solid #333;"
            bg = "#1a1a1a" if is_active else "#f9f9f9"
            txt = "white" if is_active else "#333"
            
            st.markdown(f"""
            <div style="background-color: {bg}; color: {txt}; padding: 20px; border-radius: 12px; {border} text-align: center;">
                <div style="font-weight: bold; font-size: 16px; color: {color};">{plan_data['label']}</div>
                <div style="font-size: 28px; font-weight: 700; margin: 10px 0;">{plan_data['price']}</div>
                <div style="font-size: 12px; margin-bottom: 15px;">{plan_data['limit']} requêtes / semaine</div>
            </div>
            """, unsafe_allow_html=True)
            
            if is_active:
                st.button("ACTUEL", key=f"btn_{key}", disabled=True)
            elif plan_data['link']:
                st.link_button("CHOISIR", plan_data['link'])
            else:
                if st.button("CHOISIR", key=f"btn_{key}"):
                    st.session_state.subscription_plan = key
                    st.rerun()

        with c_gratuit: show_plan("GRATUIT", PLANS["GRATUIT"], "#666")
        with c_pro: show_plan("PRO", PLANS["PRO"], "#0055FF")
        with c_ultra: show_plan("ULTRA", PLANS["ULTRA"], "#00C853")
        
        st.write("---")
        st.write("**Ma Consommation IA**")
        current_plan = PLANS[st.session_state.subscription_plan]
        limit = current_plan['limit']
        
        if limit > 9000:
             st.progress(0)
             st.caption("Illimité")
        else:
            prog = min(st.session_state.credits_used / limit, 1.0)
            st.progress(prog)
            st.caption(f"{st.session_state.credits_used} / {limit} requêtes utilisées cette semaine")

    with t3:
        st.subheader("Mentions Légales")
        st.text_area("Texte légal", height=100)

    with t4:
        with st.form("cerfa"):
            st.subheader("Données Administratives (DC1/DC2)")
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
