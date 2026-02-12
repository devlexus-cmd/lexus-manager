import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import time
import io
import datetime 
import json
import os
from fpdf import FPDF

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Lexus Enterprise", initial_sidebar_state="expanded")

# --- 2. CONFIGURATION ABONNEMENTS ---
PLANS = {
    "GRATUIT": {"limit": 3, "price": "0€", "label": "START", "link": None},
    "PRO": {"limit": 30, "price": "15€", "label": "PRO", "link": "https://buy.stripe.com/votre_lien_pro"},
    "ULTRA": {"limit": 999999, "price": "55€", "label": "BUSINESS", "link": "https://buy.stripe.com/votre_lien_ultra"}
}

# --- 3. BASE DE DONNÉES LOCALE ---
USER_DB_FILE = "users.json"

def get_db():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, 'r') as f: return json.load(f)
        except: return default_users()
    else:
        db = default_users()
        with open(USER_DB_FILE, 'w') as f: json.dump(db, f)
        return db

def default_users():
    return {
        "admin": {"password": "lexus123", "role": "admin", "email": "admin@lexus.com", "plan": "ULTRA"},
        "demo": {"password": "demo", "role": "user", "email": "client@gmail.com", "plan": "GRATUIT"}
    }

def save_user(username, data):
    current_db = get_db()
    current_db[username] = data
    with open(USER_DB_FILE, 'w') as f: json.dump(current_db, f)
    st.session_state.users_db = current_db

# --- 4. INIT VARIABLES ---
if 'users_db' not in st.session_state: st.session_state.users_db = get_db()
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'auth_view' not in st.session_state: st.session_state.auth_view = 'landing'
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'dashboard'
if 'current_project' not in st.session_state: st.session_state.current_project = None
if 'studio_mode' not in st.session_state: st.session_state.studio_mode = None
if 'company_info' not in st.session_state: 
    st.session_state.company_info = {"name": "LEXUS Enterprise", "siret": "", "address": "", "city": "", "rep_legal": "", "ca_n1": 0, "ca_n2": 0, "ca_n3": 0}

if 'subscription_plan' not in st.session_state: st.session_state.subscription_plan = "GRATUIT"
if 'credits_used' not in st.session_state: st.session_state.credits_used = 0
if 'credits_limit' not in st.session_state: st.session_state.credits_limit = PLANS["GRATUIT"]["limit"]

if 'user_criteria' not in st.session_state:
    st.session_state.user_criteria = {
        "skills": ["BTP", "Gestion"],
        "min_daily_rate": 450,
        "max_distance": 50,
        "certifications": [],
        "min_turnover_required": 0,
        "max_penalties": 5,
        "forbidden_keywords": "",
        "target_markets": ["Public"],
        "required_guarantees": "Garantie décennale",
        "payment_terms": "30 jours"
    }
if 'user_skills' not in st.session_state: st.session_state.user_skills = st.session_state.user_criteria['skills']
if 'projects' not in st.session_state: st.session_state.projects = []

# --- 5. CSS (STYLE V10.5 + ICONS STUDIO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .stApp { background-color: #FFFFFF; color: #111111; font-family: 'Inter', sans-serif; }
    .stApp > header { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* LOGO */
    .lexus-logo-text { font-weight: 300; font-size: 24px; letter-spacing: -1px; color: #000 !important; }
    .lexus-dot { color: #0055FF; font-weight: 700; font-size: 28px; line-height: 0; }
    
    /* LANDING PAGE */
    .hero-title { font-size: 56px; font-weight: 800; line-height: 1.1; margin-bottom: 20px; color: #000; letter-spacing: -2px; text-align: center; }
    .hero-subtitle { font-size: 20px; font-weight: 300; color: #666; margin-bottom: 40px; text-align: center; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5; }
    
    .feature-card { padding: 40px 30px; border: 1px solid #eee; border-radius: 12px; text-align: center; transition: 0.3s; height: 100%; display: flex; flex-direction: column; align-items: center; }
    .feature-card:hover { border-color: #0055FF; transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
    .feature-icon svg { width: 32px; height: 32px; stroke: #0055FF; margin-bottom: 20px; }
    .feature-title { font-weight: 600; font-size: 18px; margin-bottom: 10px; color: #000; }
    .feature-desc { font-size: 14px; color: #666; line-height: 1.5; }

    /* DASHBOARD CARDS */
    .kpi-card { background-color: white; border: 1px solid #E5E5E5; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); text-align: center; display: flex; flex-direction: column; justify-content: center; height: 100%; }
    .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 5px; font-weight: 600; }
    .kpi-value { font-size: 32px; font-weight: 700; color: #111; letter-spacing: -1px; }

    /* PRICING TABLE */
    .price-col { border: 1px solid #E0E0E0; border-radius: 12px; padding: 30px; text-align: center; background: #fff; transition: 0.2s; position: relative; }
    .price-col:hover { border-color: #0055FF; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transform: translateY(-2px); }
    .price-tag { font-size: 12px; font-weight: 700; color: #0055FF; letter-spacing: 1px; margin-bottom: 10px; text-transform: uppercase; }
    .price-amount { font-size: 36px; font-weight: 800; color: #111; margin-bottom: 20px; }
    .price-list { text-align: left; margin-bottom: 25px; font-size: 14px; color: #555; line-height: 1.8; }
    
    /* STUDIO CARDS (CLEAN SVG ICONS) */
    .studio-btn { border: 1px solid #E0E0E0; border-radius: 10px; padding: 25px; text-align: center; background: white; cursor: pointer; height: 100%; transition: 0.2s; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .studio-btn:hover { border-color: #0055FF; background-color: #F8FBFF; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    .studio-icon { margin-bottom: 15px; }
    .studio-icon svg { width: 32px; height: 32px; stroke: #0055FF; stroke-width: 1.5; }
    .studio-t { font-weight: 700; margin-bottom: 5px; color: #111; font-size: 16px; }
    .studio-d { font-size: 13px; color: #666; }

    /* BOUTONS & INPUTS */
    .stButton>button { background-color: transparent; color: #444; border: 1px solid transparent; text-align: left; padding-left: 0; font-weight: 500; }
    .stButton>button:hover { color: #0055FF; background-color: #F0F5FF; border-radius: 8px; padding-left: 10px; }
    
    div[data-testid="stHorizontalBlock"] .stButton>button, .primary-btn, .stFormSubmitButton>button { 
        background-color: #0055FF !important; color: white !important; text-align: center !important; 
        border-radius: 6px !important; padding: 12px 24px !important; font-weight: 600 !important; border: none !important;
        width: 100%; box-shadow: 0 4px 12px rgba(0,85,255,0.15) !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton>button:hover, .stFormSubmitButton>button:hover { background-color: #0044cc !important; transform: translateY(-1px); }
    
    section[data-testid="stSidebar"] .stButton>button { background-color: transparent !important; color: #444 !important; box-shadow: none !important; text-align: left !important; }
    section[data-testid="stSidebar"] .stButton>button:hover { background-color: #F0F5FF !important; color: #0055FF !important; }

    .stTextInput>div>div>input { background-color: #FAFAFA !important; color: #000; border: 1px solid #E0E0E0; border-radius: 8px; }
    .skill-tag { display: inline-block; padding: 5px 10px; margin: 2px; background: #F0F5FF; color: #0055FF; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid #D6E4FF; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# === PARTIE 1 : LANDING PAGE & AUTHENTIFICATION ===
# =========================================================

def login_screen():
    c1, c2 = st.columns([1, 6])
    with c1: st.markdown("<div style='padding-top:10px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
    with c2:
        sc1, sc2, sc3 = st.columns([5, 0.5, 1.5])
        if sc3.button("Se connecter", key="btn_login_home"): st.session_state.auth_view = 'login'; st.rerun()

    st.write(""); st.write(""); st.write(""); st.write("")
    st.markdown("<div class='hero-title'>L'Intelligence Artificielle pour<br><span style='color:#0055FF'>vos marchés publics.</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Centralisez vos appels d'offres. Analysez vos documents en un clic.<br>Générez vos dossiers administratifs sans erreur.</div>", unsafe_allow_html=True)
    
    c_cta1, c_cta2, c_cta3 = st.columns([1, 1, 1])
    with c_cta2:
        with st.form("hero_cta"):
            if st.form_submit_button("CRÉER UN COMPTE GRATUIT"): st.session_state.auth_view = 'signup'; st.rerun()
        st.markdown("<div style='text-align:center; font-size:12px; color:#888; margin-top:10px;'>Accès immédiat • Paiement à la consommation IA</div>", unsafe_allow_html=True)

    st.write(""); st.write(""); st.write("")
    c_f1, c_f2, c_f3 = st.columns(3)
    with c_f1: st.markdown("""<div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg></div><div class="feature-title">Analyse Sémantique</div><div class="feature-desc">Notre IA lit et comprend vos cahiers des charges. Elle extrait instantanément les critères et délais.</div></div>""", unsafe_allow_html=True)
    with c_f2: st.markdown("""<div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg></div><div class="feature-title">Gestion Administrative</div><div class="feature-desc">Fini la saisie manuelle. Lexus pré-remplit vos DC1, DC2 et documents de conformité.</div></div>""", unsafe_allow_html=True)
    with c_f3: st.markdown("""<div class="feature-card"><div class="feature-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg></div><div class="feature-title">Pilotage Financier</div><div class="feature-desc">Un tableau de bord clair pour suivre vos taux de succès et votre CA prévisionnel.</div></div>""", unsafe_allow_html=True)
    st.write(""); st.markdown("<hr style='border:0; border-top:1px solid #eee; margin: 50px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#888; font-size:12px;'>© 2026 LEXUS Enterprise.</div>", unsafe_allow_html=True)

def auth_form(mode):
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; margin-bottom:20px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; margin-bottom:30px;'>{mode}</h3>", unsafe_allow_html=True)
        with st.form("auth"):
            username = st.text_input("Identifiant / Email")
            password = st.text_input("Mot de passe", type="password")
            if mode == "Créer un compte": st.text_input("Nom de l'entreprise")
            btn_text = "SE CONNECTER" if mode == "Se connecter" else "S'INSCRIRE"
            
            if st.form_submit_button(btn_text):
                current_db = get_db()
                if mode == "Créer un compte":
                    if username in current_db: st.error("Existe déjà.")
                    else:
                        save_user(username, {"password": password, "role": "user", "plan": "GRATUIT", "email": username})
                        st.success("Compte créé !"); time.sleep(1); st.session_state.auth_view = 'login'; st.rerun()
                else:
                    if username in current_db and current_db[username]["password"] == password:
                        st.session_state.authenticated = True
                        st.session_state.user_name = username
                        st.session_state.user_role = current_db[username].get("role", "user")
                        user_plan = current_db[username].get("plan", "GRATUIT")
                        st.session_state.subscription_plan = user_plan
                        st.session_state.credits_limit = PLANS[user_plan]["limit"]
                        st.rerun()
                    else: st.error("Identifiants incorrects.")
        if st.button("← Retour"): st.session_state.auth_view = 'landing'; st.rerun()

if not st.session_state.authenticated:
    if st.session_state.auth_view == 'landing': login_screen()
    elif st.session_state.auth_view == 'login': auth_form("Se connecter")
    elif st.session_state.auth_view == 'signup': auth_form("Créer un compte")
    st.stop()

# =========================================================
# === PARTIE 2 : APPLICATION ===
# =========================================================

# --- MOTEUR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10); self.cell(0, 10, 'FORMULAIRE DC1 - LETTRE DE CANDIDATURE', align='C', new_x="LMARGIN", new_y="NEXT"); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.cell(0, 10, f'Page {self.page_no()} - Généré par LEXUS Enterprise', align='C')

def create_pdf_dc(info, project):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Helvetica", size=10); pdf.set_fill_color(245, 245, 245)
    date_str = str(datetime.date.today())
    sections = [
        ("A - POUVOIR ADJUDICATEUR", f"Client : {project['client']}\nObjet : {project['name']}\nDate : {date_str}"),
        ("B - CANDIDAT", f"Société : {info.get('name', '')}\nSIRET : {info.get('siret', '')}\nAdresse : {info.get('address', '')}"),
        ("C - CAPACITÉS", f"CA N-1 : {info.get('ca_n1', 0)} €\nCA N-2 : {info.get('ca_n2', 0)} €\nCA N-3 : {info.get('ca_n3', 0)} €"),
        ("D - ENGAGEMENT", f"Signé par {info.get('rep_legal', '')}.\nFait à {info.get('city', '')}, le {date_str}")
    ]
    for title, content in sections:
        pdf.set_font("Helvetica", 'B', 11); pdf.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT"); pdf.set_font("Helvetica", size=10); pdf.multi_cell(0, 6, content); pdf.ln(5)
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
    plan_info = PLANS.get(st.session_state.subscription_plan, PLANS["GRATUIT"])
    if st.session_state.credits_used >= plan_info['limit']: return f"⚠️ LIMITE ATTEINTE ({plan_info['limit']}/sem). Passez à l'abonnement supérieur."
    if not active_model: return "⚠️ Clé API invalide."
    try:
        model = genai.GenerativeModel(active_model)
        res = model.generate_content([prompt, image]).text
        st.session_state.credits_used += 1
        return res
    except Exception as e: return f"Erreur : {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("""<div style='margin-bottom:40px; padding-left:5px;'><span class='lexus-logo-text'>L</span><span style='color:#aaa; font-weight:200; font-size:26px;'>A</span><span class='lexus-dot'>.</span><div style='font-size:10px; letter-spacing:3px; font-weight:700; margin-top:5px; color:#444;'>LEXUS AI</div></div>""", unsafe_allow_html=True)
    if st.button("Tableau de bord"): st.session_state.page = 'dashboard'; st.rerun()
    if st.button("Lexus AI Studio"): st.session_state.page = 'studio'; st.rerun()
    if st.button("Paramètres"): st.session_state.page = 'settings'; st.rerun()
    
    # ADMIN
    if st.session_state.get('user_role') == 'admin':
        st.markdown("---"); 
        if st.button("🔴 ADMIN PANEL"): st.session_state.page = 'admin'; st.rerun()
    st.markdown("---")
    if st.button("Déconnexion"): st.session_state.authenticated = False; st.session_state.auth_view = 'landing'; st.rerun()
    # STATUS SERVEUR (SANS EMOJI)
    status_style = "color:#00C853; font-weight:bold;" if API_STATUS == "ONLINE" else "color:#FF0000; font-weight:bold;"
    st.markdown(f"<div style='font-size:10px; color:#999; margin-top:10px;'>SERVEUR : <span style='{status_style}'>{API_STATUS}</span></div>", unsafe_allow_html=True)

# --- PAGES ---

# DASHBOARD
if st.session_state.page == 'dashboard':
    st.markdown(f"## Espace <span style='color:#0055FF'>{st.session_state.company_info['name']}</span>", unsafe_allow_html=True)
    
    # CALCUL RÉEL (PAS DE CHIFFRE FICTIF)
    total = sum(p['budget'] for p in st.session_state.projects)
    nb_projets = len(st.session_state.projects)
    budget_moyen = total / nb_projets if nb_projets > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">CA PIPELINE</div><div class="kpi-value">{total:,.0f} €</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">BUDGET MOYEN</div><div class="kpi-value">{budget_moyen:,.0f} €</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">DOSSIERS ACTIFS</div><div class="kpi-value">{nb_projets}</div></div>""", unsafe_allow_html=True)
    
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
                    criteria_text = f"Compétences: {', '.join(st.session_state.user_criteria['skills'])}. CA Min requis: {st.session_state.user_criteria['min_turnover_required']}€. Pénalités Max: {st.session_state.user_criteria['max_penalties']}%."
                    res = analyze(img, f"Projet : {p['name']}. Contexte : {criteria_text}. Extrais Matching, RSE, Délai, Pénalités. Vérifie si le CA est suffisant et si les pénalités sont acceptables.")
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
    
    if st.session_state.studio_mode is None:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""<div class="studio-btn"><div class="studio-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0055FF" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path></svg></div><div class="studio-t">Analyse AO</div><div class="studio-d">Extraction critères</div></div>""", unsafe_allow_html=True)
            if st.button("Lancer", key="s1"): st.session_state.studio_mode="AO"; st.rerun()
        with c2:
            st.markdown("""<div class="studio-btn"><div class="studio-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0055FF" stroke-width="1.5"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg></div><div class="studio-t">Finance</div><div class="studio-d">Devis & Factures</div></div>""", unsafe_allow_html=True)
            if st.button("Lancer", key="s2"): st.session_state.studio_mode="Finance"; st.rerun()
        with c3:
            st.markdown("""<div class="studio-btn"><div class="studio-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0055FF" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg></div><div class="studio-t">Juridique</div><div class="studio-d">Risques & Conformité</div></div>""", unsafe_allow_html=True)
            if st.button("Lancer", key="s3"): st.session_state.studio_mode="Juridique"; st.rerun()
    else:
        if st.button("← Retour"): st.session_state.studio_mode = None; st.rerun()
        st.markdown(f"### Mode : {st.session_state.studio_mode}")
        f = st.file_uploader("Document", type=['png', 'jpg', 'jpeg'])
        if f and st.button("ANALYSER"):
            im = Image.open(f); st.image(im, width=200)
            with st.spinner("Traitement..."): st.write(analyze(im, f"Mode {st.session_state.studio_mode}."))

# ADMIN
elif st.session_state.page == 'admin':
    st.title("Console Administration")
    current_db = get_db()
    users_data = [{"Utilisateur": u, "Email": d.get("email"), "Plan": d.get("plan"), "Rôle": d.get("role")} for u, d in current_db.items()]
    st.table(pd.DataFrame(users_data))
    c1, c2, c3 = st.columns(3)
    with c1: target_user = st.selectbox("Utilisateur", list(current_db.keys()))
    with c2: target_plan = st.selectbox("Plan", ["GRATUIT", "PRO", "ULTRA"])
    with c3: 
        st.write(""); 
        if st.button("Mettre à jour"): update_plan(target_user, target_plan); st.success("OK"); time.sleep(1); st.rerun()

# PARAMETRES
elif st.session_state.page == 'settings':
    st.title("Paramètres Généraux")
    t1, t2, t3, t4 = st.tabs(["Critères", "Abonnements", "Mentions", "CERFA"])
    
    with t1:
        st.subheader("Configuration IA Expert")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Technique**")
            new_skill = st.text_input("Compétence", placeholder="Ajouter...")
            if st.button("Ajouter"): st.session_state.user_skills.append(new_skill); st.rerun()
            for s in st.session_state.user_skills: st.markdown(f"<span class='skill-tag'>{s}</span>", unsafe_allow_html=True)
            if st.button("Reset"): st.session_state.user_skills = []; st.rerun()
            st.number_input("CA Minimum requis par marché (€)", value=st.session_state.user_criteria['min_turnover_required'])
        with c2:
            st.markdown("**Administratif**")
            st.text_area("Certifications (Qualibat, ISO...)", height=100)
            st.slider("Pénalités max acceptées (%)", 0, 100, 5)
            st.text_input("Mots-clés interdits", placeholder="Amiante, Nucléaire...")
            st.multiselect("Marchés cibles", ["Public", "Privé"], default=["Public"])
            st.text_input("Garanties exigées", placeholder="Décennale...")

    with t2:
        st.subheader("Plans Tarifaires")
        cols = st.columns(3)
        def p_card(k, col):
            p = PLANS[k]
            with col:
                st.markdown(f"""<div class="price-col"><div class="price-tag">{p['label']}</div><div class="price-amount">{p['price']}</div><div class="price-list"><li>{p['limit']} analyses/sem</li></div></div>""", unsafe_allow_html=True)
                if p['link']: st.link_button("CHOISIR", p['link'])
                else: st.button("ACTUEL", key=k, disabled=True)
        p_card("GRATUIT", cols[0]); p_card("PRO", cols[1]); p_card("ULTRA", cols[2])

    with t3: st.text_area("Mentions Légales", height=100)
    with t4:
        with st.form("cerfa"):
            i = st.session_state.company_info
            c1, c2 = st.columns(2)
            i['name'] = c1.text_input("Dénomination", value=i['name']); i['siret'] = c2.text_input("SIRET", value=i['siret'])
            i['address'] = c1.text_input("Adresse", value=i['address']); i['city'] = c2.text_input("Ville", value=i['city'])
            i['rep_legal'] = c1.text_input("Représentant", value=i['rep_legal'])
            c3, c4, c5 = st.columns(3)
            i['ca_n1'] = c3.number_input("CA N-1", value=i['ca_n1']); i['ca_n2'] = c4.number_input("CA N-2", value=i['ca_n2']); i['ca_n3'] = c5.number_input("CA N-3", value=i.get('ca_n3', 0))
            if st.form_submit_button("SAUVEGARDER"): st.session_state.company_info = i; st.success("OK")
