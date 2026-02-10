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
    "GRATUIT": {"limit": 3, "price": "0€", "label": "START", "link": None, "features": ["3 analyses / semaine", "Tableau de bord basique"]},
    "PRO": {"limit": 30, "price": "15€", "label": "PRO", "link": "https://buy.stripe.com/votre_lien_pro", "features": ["30 analyses / semaine", "Export PDF illimité", "Support prioritaire"]},
    "ULTRA": {"limit": 999999, "price": "55€", "label": "BUSINESS", "link": "https://buy.stripe.com/votre_lien_ultra", "features": ["Analyses illimitées", "IA Modèle Supérieur", "API Access"]}
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
if 'company_info' not in st.session_state: 
    # AJOUT DU CA N-3 ICI
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
        "market_type": ["Public", "Privé"], # NOUVEAU
        "forbidden_keywords": [] # NOUVEAU
    }
if 'user_skills' not in st.session_state: st.session_state.user_skills = st.session_state.user_criteria['skills']
if 'projects' not in st.session_state: st.session_state.projects = []

# --- 5. CSS PRO (DENSE & PRÉCIS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp { background-color: #F8F9FA; color: #111111; font-family: 'Inter', sans-serif; }
    .stApp > header { visibility: hidden; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { 
        background-color: #FFFFFF; 
        border-right: 1px solid #E5E5E5;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* LOGO */
    .lexus-logo-text { font-weight: 300; font-size: 22px; letter-spacing: -0.5px; color: #000 !important; }
    .lexus-dot { color: #0055FF; font-weight: 700; font-size: 28px; line-height: 0; }
    
    /* BOUTONS NAVIGATION */
    .stButton>button { 
        background-color: transparent; color: #555; border: none; text-align: left; 
        padding: 8px 15px; font-weight: 500; border-radius: 6px; margin-bottom: 2px;
    }
    .stButton>button:hover { color: #0055FF; background-color: #F0F5FF; font-weight: 600; }
    
    /* BOUTONS ACTIONS BLEUS */
    .primary-btn { 
        background-color: #0055FF !important; color: white !important; 
        border-radius: 6px !important; padding: 10px 20px !important; 
        font-weight: 600 !important; border: none !important;
        box-shadow: 0 4px 12px rgba(0,85,255,0.2) !important;
    }

    /* CARTES DASHBOARD */
    .kpi-card { 
        background-color: white; border: 1px solid #E5E5E5; padding: 24px; 
        border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        display: flex; flex-direction: column; height: 100%;
    }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #888; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #111; }
    .kpi-trend { font-size: 12px; color: #00C853; font-weight: 500; margin-top: 5px; }

    /* STUDIO CARDS */
    .studio-card {
        background: white; border: 1px solid #E5E5E5; border-radius: 12px; padding: 25px;
        text-align: center; transition: all 0.2s; cursor: pointer; height: 100%;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .studio-card:hover { border-color: #0055FF; box-shadow: 0 5px 20px rgba(0,85,255,0.1); transform: translateY(-3px); }
    .studio-icon { font-size: 32px; color: #0055FF; margin-bottom: 15px; }
    .studio-title { font-weight: 600; font-size: 16px; margin-bottom: 5px; color: #111; }
    .studio-desc { font-size: 12px; color: #666; line-height: 1.4; }

    /* PRICING TABLE */
    .pricing-col {
        background: white; border: 1px solid #E5E5E5; border-radius: 16px; padding: 30px;
        text-align: center; transition: 0.3s; position: relative;
    }
    .pricing-col.featured { border: 2px solid #0055FF; box-shadow: 0 10px 40px rgba(0,85,255,0.1); transform: scale(1.02); z-index: 10; }
    .p-name { font-size: 14px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .p-price { font-size: 42px; font-weight: 800; color: #111; margin: 15px 0; }
    .p-feat { text-align: left; margin: 20px 0; font-size: 14px; color: #555; }
    .p-feat li { margin-bottom: 10px; list-style: none; }
    
    /* INPUTS */
    .stTextInput>div>div>input { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 8px; color: #111; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# === FONCTIONS ===
# =========================================================

# MOTEUR PDF (AVEC CA N-3 AJOUTÉ)
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10); self.cell(0, 10, 'FORMULAIRE DC1 - LETTRE DE CANDIDATURE', align='C', new_x="LMARGIN", new_y="NEXT"); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf_dc(info, project):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Helvetica", size=10); pdf.set_fill_color(248, 249, 250)
    date_str = str(datetime.date.today())
    
    # Bloc Identité
    pdf.set_font("Helvetica", 'B', 11); pdf.cell(0, 8, "A - POUVOIR ADJUDICATEUR", fill=True, new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
    pdf.set_font("Helvetica", size=10); pdf.multi_cell(0, 6, f"Client : {project['client']}\nObjet : {project['name']}\nDate : {date_str}"); pdf.ln(5)
    
    # Bloc Candidat
    pdf.set_font("Helvetica", 'B', 11); pdf.cell(0, 8, "B - CANDIDAT", fill=True, new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
    pdf.set_font("Helvetica", size=10); pdf.multi_cell(0, 6, f"Société : {info.get('name', '')}\nSIRET : {info.get('siret', '')}\nAdresse : {info.get('address', '')}"); pdf.ln(5)
    
    # Bloc Capacités (AVEC CA N-3)
    pdf.set_font("Helvetica", 'B', 11); pdf.cell(0, 8, "C - CAPACITÉS FINANCIÈRES", fill=True, new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, f"CA N-1 : {info.get('ca_n1', 0)} EUR\nCA N-2 : {info.get('ca_n2', 0)} EUR\nCA N-3 : {info.get('ca_n3', 0)} EUR") # AJOUT CA N-3
    pdf.ln(5)
    
    return bytes(pdf.output())

# IA CONNECTÉE
try:
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if api_key:
        genai.configure(api_key=api_key)
        m = [model.name for model in genai.list_models() if 'generateContent' in model.supported_generation_methods]
        # Auto-detect meilleur modèle
        if "models/gemini-1.5-flash" in m: active_model = "models/gemini-1.5-flash"
        elif "models/gemini-1.5-pro" in m: active_model = "models/gemini-1.5-pro"
        else: active_model = m[0] if m else None
        API_STATUS = "ONLINE"
    else: active_model = None; API_STATUS = "OFFLINE"
except: active_model = None; API_STATUS = "LOCAL"

def analyze(image, prompt):
    plan_info = PLANS.get(st.session_state.subscription_plan, PLANS["GRATUIT"])
    if st.session_state.credits_used >= plan_info['limit']: return f"⚠️ LIMITE ATTEINTE. Upgradez votre plan."
    if not active_model: return "⚠️ Clé API invalide."
    try:
        model = genai.GenerativeModel(active_model)
        res = model.generate_content([prompt, image]).text
        st.session_state.credits_used += 1
        return res
    except Exception as e: return f"Erreur : {str(e)}"

# =========================================================
# === INTERFACE ===
# =========================================================

# LANDING & LOGIN (CODE IDENTIQUE V10.5)
def login_screen():
    c1, c2 = st.columns([1, 6])
    with c1: st.markdown("<div style='padding-top:10px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
    with c2:
        sc1, sc2, sc3 = st.columns([5, 0.5, 1.5])
        if sc3.button("Se connecter", key="btn_login_home"): st.session_state.auth_view = 'login'; st.rerun()

    st.write(""); st.write(""); st.write("")
    st.markdown("<div class='hero-title'>L'Intelligence Artificielle pour<br><span style='color:#0055FF'>vos marchés publics.</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Centralisez vos appels d'offres. Analysez vos documents en un clic.<br>Générez vos dossiers administratifs sans erreur.</div>", unsafe_allow_html=True)
    
    c_cta1, c_cta2, c_cta3 = st.columns([1, 1, 1])
    with c_cta2:
        with st.form("hero_cta"):
            if st.form_submit_button("CRÉER UN COMPTE GRATUIT"): st.session_state.auth_view = 'signup'; st.rerun()
        st.markdown("<div style='text-align:center; font-size:12px; color:#888; margin-top:10px;'>Accès immédiat • Paiement à la consommation IA</div>", unsafe_allow_html=True)
    
    st.write(""); st.write("")
    # (Features Grid conservée...)

def auth_form(mode):
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br><div style='text-align:center; margin-bottom:20px;'><span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center; margin-bottom:30px;'>{mode}</h3>", unsafe_allow_html=True)
        with st.form("auth"):
            u = st.text_input("Email"); p = st.text_input("Mot de passe", type="password")
            if mode == "Créer un compte": st.text_input("Société")
            if st.form_submit_button("VALIDER"):
                if mode=="Créer un compte": save_user(u, {"password":p,"role":"user","plan":"GRATUIT"}); st.session_state.auth_view='login'; st.success("Compte créé !"); time.sleep(1); st.rerun()
                elif u in st.session_state.users_db and st.session_state.users_db[u]["password"]==p:
                    st.session_state.authenticated=True; st.session_state.user_name=u; st.session_state.subscription_plan=st.session_state.users_db[u].get("plan","GRATUIT"); st.rerun()
                else: st.error("Erreur.")
        if st.button("Retour"): st.session_state.auth_view='landing'; st.rerun()

if not st.session_state.authenticated:
    if st.session_state.auth_view == 'landing': login_screen()
    elif st.session_state.auth_view in ['login', 'signup']: auth_form("Connexion" if st.session_state.auth_view=='login' else "Créer un compte")
    st.stop()

# --- APP ---

# SIDEBAR
with st.sidebar:
    st.markdown("""<div style='margin-bottom:40px; padding-left:5px;'><span class='lexus-logo-text'>L</span><span style='color:#aaa; font-weight:200; font-size:26px;'>A</span><span class='lexus-dot'>.</span><div style='font-size:10px; letter-spacing:3px; font-weight:700; margin-top:5px; color:#444;'>LEXUS AI</div></div>""", unsafe_allow_html=True)
    if st.button("Tableau de bord"): st.session_state.page = 'dashboard'; st.rerun()
    if st.button("Lexus AI Studio"): st.session_state.page = 'studio'; st.rerun()
    if st.button("Paramètres"): st.session_state.page = 'settings'; st.rerun()
    st.markdown("---")
    if st.button("Déconnexion"): st.session_state.authenticated = False; st.rerun()
    
# DASHBOARD (DENSIFIÉ)
if st.session_state.page == 'dashboard':
    st.markdown(f"## Espace <span style='color:#0055FF'>{st.session_state.company_info['name']}</span>", unsafe_allow_html=True)
    
    # 1. KPIs
    total = sum(p['budget'] for p in st.session_state.projects)
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">CA PRÉVISIONNEL</div><div class="kpi-value">{total:,.0f} €</div><div class="kpi-trend">Basé sur {len(st.session_state.projects)} dossiers</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">CRÉDITS IA RESTANTS</div><div class="kpi-value">{PLANS[st.session_state.subscription_plan]['limit'] - st.session_state.credits_used}</div><div class="kpi-trend">Plan {st.session_state.subscription_plan}</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown(f"""<div class="kpi-card"><div class="kpi-label">ACTIONS REQUISES</div><div class="kpi-value">3</div><div class="kpi-trend" style="color:orange;">Urgent</div></div>""", unsafe_allow_html=True)
    
    # 2. ACTIVITÉ RÉCENTE (POUR REMPLIR LE VIDE)
    st.write(""); st.subheader("Fil d'actualité")
    st.info("ℹ️ **10:42** - Analyse IA terminée pour le dossier 'Groupe Alpha'.")
    st.info("ℹ️ **Hier** - Nouveau document ajouté dans 'Rénovation Siège'.")
    
    # 3. PROJETS
    st.write(""); st.caption("DOSSIERS EN COURS")
    for p in st.session_state.projects:
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{p['name']}**<br><span style='color:#888; font-size:12px;'>{p['client']}</span>", unsafe_allow_html=True)
            c2.markdown(f"**{p['budget']:,.0f} €**", unsafe_allow_html=True)
            if c3.button("Ouvrir", key=f"open_{p['id']}"): st.session_state.current_project = p; st.session_state.page = 'project'; st.rerun()
            st.markdown("<hr style='margin:5px 0; border-color:#eee;'>", unsafe_allow_html=True)
            
    with st.expander("Ajouter un nouvel appel d'offre +"):
        with st.form("new_ao"):
            n_name = st.text_input("Nom"); n_client = st.text_input("Client"); n_budget = st.number_input("Budget", value=0)
            if st.form_submit_button("Créer"):
                st.session_state.projects.append({"id": len(st.session_state.projects)+1, "name": n_name, "client": n_client, "budget": n_budget, "status": "NOUVEAU", "analysis_done": False, "match": 0, "rse": "-", "delay": "-", "penalty": "-"})
                st.rerun()

# PROJECT DETAIL (UNCHANGED)
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
        uploaded_file = st.file_uploader("Importer le DCE (Image)", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            img = Image.open(uploaded_file); st.image(img, caption="Document chargé", width=200)
            if st.button("LANCER L'ANALYSE IA", key="btn_ana_proj"):
                with st.spinner("Extraction..."):
                    res = analyze(img, f"Projet : {p['name']}. Extrais Matching, RSE, Délai, Pénalités.")
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

# LEXUS AI STUDIO (REFONDU & DESIGNÉ)
elif st.session_state.page == 'studio':
    st.title("Lexus AI Studio")
    st.write("Sélectionnez un outil pour lancer l'intelligence artificielle.")
    
    # SELECTEUR DE MODE CLAIR
    mode_studio = st.radio("Mode", ["Analyse Globale", "Extraction Chiffres", "Conformité Juridique", "Rédaction Mail"], horizontal=True)
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"### 1. Import ({mode_studio})")
        # Carte d'upload stylisée
        f = st.file_uploader("Déposez votre document ici", type=['png', 'jpg', 'jpeg'])
        
        if f:
            im = Image.open(f); st.image(im, width=300)
            st.write("")
            if st.button("LANCER L'ANALYSE", key="btn_studio"):
                with st.spinner("Lexus AI travaille..."): st.session_state['studio_res'] = analyze(im, f"Mode expert: {mode_studio}")
    
    with c2:
        st.markdown("### 2. Résultat")
        if 'studio_res' in st.session_state:
            st.success("Terminé")
            st.text_area("Rapport", st.session_state['studio_res'], height=500)
        else:
            st.info("Le résultat s'affichera ici.")

# PARAMETRES (AVEC CERFA COMPLET & ABONNEMENTS DESIGN)
elif st.session_state.page == 'settings':
    st.title("Paramètres Généraux")
    t1, t2, t3, t4 = st.tabs(["Critères Experts", "Abonnements", "Mentions Légales", "Données CERFA"])
    
    # 1. CRITÈRES EXPERTS (COMPLET)
    with t1:
        st.subheader("Configuration de l'IA")
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("##### Technique")
            st.multiselect("Compétences Clés", ["BTP", "Gros Oeuvre", "Elec", "Plomberie", "Finances", "Audit"], default=["BTP"])
            st.text_area("Certifications (Qualibat...)", height=100)
        with c_right:
            st.markdown("##### Marché & Risques")
            st.multiselect("Type de Marché visé", ["Public", "Privé", "Mixte"], default=["Public"])
            st.number_input("CA Minimum du marché (€)", value=0)
            st.slider("Pénalités max acceptées (%)", 0, 100, 5)

    # 2. ABONNEMENTS (DESIGN TABLEAU DE PRIX)
    with t2:
        st.subheader("Mon Offre")
        
        # Affichage Grid Pricing
        cols = st.columns(3)
        
        # PLAN GRATUIT
        with cols[0]:
            st.markdown(f"""
            <div class="pricing-col">
                <div class="p-name">START</div>
                <div class="p-price">0€</div>
                <div class="p-feat"><li>3 essais / sem</li><li>Dashboard limité</li></div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.subscription_plan == "GRATUIT": st.button("ACTUEL", disabled=True, key="p1")
            else: 
                if st.button("CHOISIR", key="p1"): st.session_state.subscription_plan="GRATUIT"; st.rerun()

        # PLAN PRO
        with cols[1]:
            st.markdown(f"""
            <div class="pricing-col featured">
                <div class="p-name" style="color:#0055FF">PRO</div>
                <div class="p-price">15€<small style="font-size:14px; color:#888">/mois</small></div>
                <div class="p-feat"><li>30 analyses / sem</li><li>Export PDF</li><li>Support</li></div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.subscription_plan == "PRO": st.button("ACTUEL", disabled=True, key="p2")
            else: st.link_button("S'ABONNER", PLANS["PRO"]["link"])

        # PLAN ULTRA
        with cols[2]:
            st.markdown(f"""
            <div class="pricing-col">
                <div class="p-name">BUSINESS</div>
                <div class="p-price">55€<small style="font-size:14px; color:#888">/mois</small></div>
                <div class="p-feat"><li>Illimité</li><li>IA Prioritaire</li><li>API Access</li></div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.subscription_plan == "ULTRA": st.button("ACTUEL", disabled=True, key="p3")
            else: st.link_button("S'ABONNER", PLANS["ULTRA"]["link"])

    # 3. CERFA (AVEC CA N-3)
    with t4:
        with st.form("cerfa"):
            st.subheader("Données Administratives (DC1/DC2)")
            i = st.session_state.company_info
            c1, c2 = st.columns(2)
            i['name'] = c1.text_input("Dénomination", value=i['name']); i['siret'] = c2.text_input("SIRET", value=i['siret'])
            i['address'] = c1.text_input("Adresse", value=i['address']); i['city'] = c2.text_input("Ville", value=i['city'])
            i['rep_legal'] = c1.text_input("Représentant", value=i['rep_legal'])
            st.markdown("**Chiffres d'affaires**")
            c3, c4, c5 = st.columns(3)
            i['ca_n1'] = c3.number_input("CA N-1", value=i['ca_n1']); i['ca_n2'] = c4.number_input("CA N-2", value=i['ca_n2'])
            i['ca_n3'] = c5.number_input("CA N-3", value=i.get('ca_n3', 0)) # Ajout N-3
            
            if st.form_submit_button("SAUVEGARDER"): 
                st.session_state.company_info = i; st.success("OK")
