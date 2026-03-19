# ⚠️ BLOC DIAGNOSTIC — à supprimer après résolution
import streamlit as st
 
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 DIAGNOSTIC**")
 
# Test 1 : package anthropic installé ?
try:
    import anthropic
    st.sidebar.success("✅ Package `anthropic` installé")
except ImportError:
    st.sidebar.error("❌ Package `anthropic` NON installé — vérifiez requirements.txt")
 
# Test 2 : clé présente dans les secrets ?
try:
    key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if key:
        st.sidebar.success(f"✅ Clé trouvée : {key[:12]}...")
    else:
        st.sidebar.error("❌ ANTHROPIC_API_KEY absente des secrets")
except Exception as e:
    st.sidebar.error(f"❌ Erreur secrets : {e}")
 
# Test 3 : clé valide (appel test à l'API) ?
try:
    import anthropic as ac
    key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if key:
        client = ac.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": "dis ok"}]
        )
        st.sidebar.success("✅ API Claude répond correctement")
except ac.AuthenticationError:
    st.sidebar.error("❌ Clé invalide (AuthenticationError)")
except ac.RateLimitError:
    st.sidebar.warning("⚠️ Quota atteint mais la clé est valide")
except Exception as e:
    st.sidebar.error(f"❌ Erreur API : {e}")
 
st.sidebar.markdown("---")
# FIN BLOC DIAGNOSTIC
import anthropic
from PIL import Image
import pandas as pd
import time
import io
import base64
import datetime
import json
import os
import re
import urllib.request

# Import PDF libs
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, BooleanObject
    PDF_FILL_AVAILABLE = True
except ImportError:
    PDF_FILL_AVAILABLE = False

# ============================================================
# 1. CONFIG
# ============================================================
st.set_page_config(
    layout="wide",
    page_title="Lexus Enterprise",
    initial_sidebar_state="expanded",
    page_icon="🏛️"
)

# ============================================================
# 2. PLANS
# ============================================================
PLANS = {
    "GRATUIT": {"limit": 3,      "price": "0€",  "label": "START",    "link": None},
    "PRO":     {"limit": 30,     "price": "15€", "label": "PRO",      "link": "https://buy.stripe.com/votre_lien_pro"},
    "ULTRA":   {"limit": 999999, "price": "55€", "label": "BUSINESS", "link": "https://buy.stripe.com/votre_lien_ultra"},
}

# ============================================================
# 3. BASE DE DONNÉES LOCALE
# ============================================================
USER_DB_FILE = "users.json"

def get_db():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return _default_users()
    db = _default_users()
    with open(USER_DB_FILE, "w") as f:
        json.dump(db, f)
    return db

def _default_users():
    return {
        "admin": {"password": "lexus123", "role": "admin",  "email": "admin@lexus.com",  "plan": "ULTRA"},
        "demo":  {"password": "demo",     "role": "user",   "email": "client@gmail.com", "plan": "GRATUIT"},
    }

def save_user(username, data):
    db = get_db()
    db[username] = data
    with open(USER_DB_FILE, "w") as f:
        json.dump(db, f)
    st.session_state.users_db = db

def update_plan(username, plan):
    db = get_db()
    if username in db:
        db[username]["plan"] = plan
        with open(USER_DB_FILE, "w") as f:
            json.dump(db, f)
        st.session_state.users_db = db

# ============================================================
# 4. SESSION STATE INIT
# ============================================================
_defaults = {
    "users_db":          get_db(),
    "authenticated":     False,
    "auth_view":         "landing",
    "user":              None,
    "page":              "dashboard",
    "current_project":   None,
    "studio_mode":       None,
    "company_info": {
        "name": "Mon Entreprise", "siret": "", "address": "",
        "city": "", "rep_legal": "", "ca_n1": 0, "ca_n2": 0, "ca_n3": 0
    },
    "subscription_plan": "GRATUIT",
    "credits_used":      0,
    "credits_limit":     PLANS["GRATUIT"]["limit"],
    "projects":          [],
    "user_criteria": {
        "skills": ["BTP", "Gestion"], "min_daily_rate": 450,
        "max_distance": 50, "certifications": [],
        "min_turnover_required": 0, "max_penalties": 5,
        "forbidden_keywords": "", "target_markets": ["Public"],
        "required_guarantees": "Garantie décennale", "payment_terms": "30 jours",
    },
    "user_skills":       ["BTP", "Gestion"],
    "dc1_download_tried": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# 5. CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

.stApp { background:#fff; color:#111; font-family:'Inter',sans-serif; }
.stApp > header, #MainMenu, footer { visibility:hidden; }

/* LOGO */
.lexus-logo-text { font-weight:300; font-size:24px; letter-spacing:-1px; color:#000 !important; }
.lexus-dot { color:#0055FF; font-weight:700; font-size:28px; line-height:0; }

/* HERO */
.hero-title { font-size:56px; font-weight:800; line-height:1.1; margin-bottom:20px; color:#000;
              letter-spacing:-2px; text-align:center; }
.hero-subtitle { font-size:20px; font-weight:300; color:#666; margin-bottom:40px; text-align:center;
                 max-width:700px; margin-left:auto; margin-right:auto; line-height:1.5; }

/* FEATURE CARDS */
.feature-card { padding:40px 30px; border:1px solid #eee; border-radius:12px; text-align:center;
                transition:.3s; height:100%; display:flex; flex-direction:column; align-items:center; }
.feature-card:hover { border-color:#0055FF; transform:translateY(-5px); box-shadow:0 10px 30px rgba(0,0,0,.05); }
.feature-icon svg { width:32px; height:32px; stroke:#0055FF; margin-bottom:20px; }
.feature-title { font-weight:600; font-size:18px; margin-bottom:10px; color:#000; }
.feature-desc  { font-size:14px; color:#666; line-height:1.5; }

/* KPI CARDS */
.kpi-card { background:#fff; border:1px solid #E5E5E5; padding:24px; border-radius:12px;
            box-shadow:0 2px 8px rgba(0,0,0,.02); text-align:center; }
.kpi-label { font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#888;
             margin-bottom:5px; font-weight:600; }
.kpi-value { font-size:32px; font-weight:700; color:#111; letter-spacing:-1px; }

/* RESULT CARDS */
.result-card { background:#FAFAFA; border:1px solid #EAEAEA; padding:20px; border-radius:10px;
               margin-bottom:15px; }
.result-label { font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#666;
                margin-bottom:5px; font-weight:600; }
.result-value { font-size:20px; font-weight:700; color:#0055FF; word-wrap:break-word; line-height:1.3; }

/* PRICING */
.price-col { border:1px solid #E0E0E0; border-radius:12px; padding:30px; text-align:center;
             background:#fff; transition:.2s; }
.price-col:hover { border-color:#0055FF; box-shadow:0 10px 30px rgba(0,0,0,.05); transform:translateY(-2px); }
.price-tag    { font-size:12px; font-weight:700; color:#0055FF; letter-spacing:1px;
                margin-bottom:10px; text-transform:uppercase; }
.price-amount { font-size:36px; font-weight:800; color:#111; margin-bottom:20px; }
.price-list   { text-align:left; margin-bottom:25px; font-size:14px; color:#555; line-height:1.8;
                list-style:none; padding:0; }

/* STUDIO */
.studio-btn { border:1px solid #E0E0E0; border-radius:10px; padding:20px; text-align:center;
              background:#fff; cursor:pointer; height:100%; transition:.2s; display:flex;
              flex-direction:column; align-items:center; justify-content:center; }
.studio-btn:hover { border-color:#0055FF; background:#F8FBFF; box-shadow:0 4px 15px rgba(0,0,0,.03); }
.studio-t { font-weight:700; margin-bottom:5px; color:#111; font-size:16px; }
.studio-d { font-size:13px; color:#666; }

/* SKILL TAG */
.skill-tag { display:inline-block; padding:5px 10px; margin:2px; background:#F0F5FF;
             color:#0055FF; border-radius:6px; font-size:12px; font-weight:600;
             border:1px solid #D6E4FF; }

/* DC1 STATUS BOX */
.dc1-status { padding:12px 16px; border-radius:8px; font-size:13px; margin-bottom:10px; }
.dc1-ok   { background:#E8F5E9; border:1px solid #A5D6A7; color:#2E7D32; }
.dc1-warn { background:#FFF8E1; border:1px solid #FFE082; color:#E65100; }

/* BUTTONS */
.stButton>button { background:transparent; color:#444; border:1px solid transparent;
                   text-align:left; padding-left:0; font-weight:500; }
.stButton>button:hover { color:#0055FF; background:#F0F5FF; border-radius:8px; padding-left:10px; }

div[data-testid="stHorizontalBlock"] .stButton>button,
.stFormSubmitButton>button {
    background:#0055FF !important; color:#fff !important; text-align:center !important;
    border-radius:6px !important; padding:12px 24px !important; font-weight:600 !important;
    border:none !important; width:100%; box-shadow:0 4px 12px rgba(0,85,255,.15) !important;
}
div[data-testid="stHorizontalBlock"] .stButton>button:hover,
.stFormSubmitButton>button:hover { background:#0044cc !important; transform:translateY(-1px); }

section[data-testid="stSidebar"] .stButton>button {
    background:transparent !important; color:#444 !important; box-shadow:none !important;
    text-align:left !important;
}
section[data-testid="stSidebar"] .stButton>button:hover {
    background:#F0F5FF !important; color:#0055FF !important;
}
.stTextInput>div>div>input { background:#FAFAFA !important; color:#000; border:1px solid #E0E0E0; border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 6. DC1 OFFICIEL — TÉLÉCHARGEMENT & REMPLISSAGE
# ============================================================

DC1_LOCAL_PATH = "dc1_officiel.pdf"

# URL officielle du formulaire DC1 (Ministère de l'Économie)
DC1_OFFICIAL_URLS = [
    "https://www.economie.gouv.fr/files/files/directions_services/daj/marches_publics/formulaires/DC/DC1.pdf",
    "https://www.marches-publics.gouv.fr/formulaires/DC1.pdf",
]

# Correspondance complète des champs AcroForm du DC1 officiel
# (noms exacts vérifiés sur le formulaire Cerfa 12156*06)
DC1_FIELD_MAP = {
    # Section A — Identification de l'acheteur public
    "Intitulé de la consultation": "objet",
    "Objet du marché": "objet",
    "Numéro de référence de la consultation": "",
    # Section B — Identification du candidat
    "Dénomination": "name",
    "Forme juridique": "forme_juridique",
    "Capital social": "",
    "Adresse": "address",
    "Code postal": "code_postal",
    "Commune": "city",
    "Numéro SIRET": "siret",
    "Code APE ou NAF": "ape",
    "Numéro TVA intracommunautaire": "tva",
    # Section D — Signature
    "Fait à": "city",
    "Le": "date_today",
    "Nom Prénom": "rep_legal",
    "Qualité": "qualite_signataire",
}

def _get_dc1_field_value(field_key: str, info: dict, project: dict) -> str:
    """Résoud la valeur d'un champ DC1 à partir de nos données."""
    mapping = {
        "objet":             project.get("name", ""),
        "name":              info.get("name", ""),
        "address":           info.get("address", ""),
        "city":              info.get("city", ""),
        "code_postal":       info.get("code_postal", ""),
        "siret":             info.get("siret", ""),
        "ape":               info.get("ape", ""),
        "tva":               info.get("tva", ""),
        "rep_legal":         info.get("rep_legal", ""),
        "qualite_signataire":info.get("qualite_signataire", "Gérant"),
        "forme_juridique":   info.get("forme_juridique", ""),
        "date_today":        datetime.date.today().strftime("%d/%m/%Y"),
        "":                  "",
    }
    key = DC1_FIELD_MAP.get(field_key, "")
    return mapping.get(key, "")


def try_download_dc1() -> bool:
    """
    Tente de télécharger le DC1 officiel depuis les URLs gouvernementales.
    Retourne True si le fichier est disponible localement.
    """
    if os.path.exists(DC1_LOCAL_PATH) and os.path.getsize(DC1_LOCAL_PATH) > 10_000:
        return True

    if st.session_state.get("dc1_download_tried"):
        return False

    st.session_state.dc1_download_tried = True

    for url in DC1_OFFICIAL_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            if len(data) > 10_000:  # fichier cohérent
                with open(DC1_LOCAL_PATH, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            continue
    return False


def _smart_fill_field(writer: "PdfWriter", fields: dict, target_key: str, value: str):
    """
    Cherche le bon champ AcroForm par correspondance partielle insensible à la casse,
    puis remplit tous les champs correspondants avec la valeur.
    """
    if not value:
        return
    target_lower = target_key.lower()
    for field_name in fields.keys():
        fn_lower = field_name.lower()
        if target_lower in fn_lower or fn_lower in target_lower:
            try:
                writer.update_page_form_field_values(
                    writer.pages[0], {field_name: value}, auto_regenerate=False
                )
            except Exception:
                pass


def fill_dc1_official(info: dict, project: dict) -> bytes | None:
    """
    Remplit le PDF officiel DC1 (AcroForm) avec les données de l'utilisateur.
    Retourne les bytes du PDF rempli (champs toujours modifiables),
    ou None si le template n'est pas disponible.
    """
    if not PDF_FILL_AVAILABLE:
        return None

    available = try_download_dc1()
    if not available:
        return None

    try:
        reader = PdfReader(DC1_LOCAL_PATH)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # Cloner l'AcroForm depuis le reader pour conserver tous les champs
        if "/AcroForm" in reader.trailer["/Root"]:
            writer._root_object.update({
                NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
            })

        fields = reader.get_fields() or {}

        # Construction du dictionnaire de remplissage par correspondance intelligente
        fill_dict = {}

        # Valeurs à injecter
        values_by_alias = {
            # Libellés fréquents dans le DC1 officiel
            "objet":         project.get("name", ""),
            "intitulé":      project.get("name", ""),
            "marché":        project.get("name", ""),
            "dénomination":  info.get("name", ""),
            "société":       info.get("name", ""),
            "candidat":      info.get("name", ""),
            "siret":         info.get("siret", ""),
            "adresse":       info.get("address", ""),
            "commune":       info.get("city", ""),
            "ville":         info.get("city", ""),
            "fait à":        info.get("city", ""),
            "fait_a":        info.get("city", ""),
            "code postal":   info.get("code_postal", ""),
            "ape":           info.get("ape", ""),
            "naf":           info.get("ape", ""),
            "tva":           info.get("tva", ""),
            "représentant":  info.get("rep_legal", ""),
            "signataire":    info.get("rep_legal", ""),
            "nom prénom":    info.get("rep_legal", ""),
            "le":            datetime.date.today().strftime("%d/%m/%Y"),
            "date":          datetime.date.today().strftime("%d/%m/%Y"),
            "qualité":       info.get("qualite_signataire", "Gérant"),
            "forme":         info.get("forme_juridique", ""),
            "capital":       str(info.get("capital", "")),
            "ca n-1":        str(info.get("ca_n1", "")),
            "ca n-2":        str(info.get("ca_n2", "")),
            "ca n-3":        str(info.get("ca_n3", "")),
        }

        for field_name in fields.keys():
            fn_lower = field_name.lower().strip()
            for alias, val in values_by_alias.items():
                if alias in fn_lower and val:
                    fill_dict[field_name] = val
                    break  # on ne surécrit pas avec un alias moins prioritaire

        if fill_dict:
            # Remplir page par page (le DC1 peut avoir plusieurs pages)
            for page_idx in range(len(writer.pages)):
                try:
                    writer.update_page_form_field_values(
                        writer.pages[page_idx], fill_dict, auto_regenerate=False
                    )
                except Exception:
                    pass

        # NeedAppearances → les lecteurs PDF régénèrent l'affichage des valeurs
        # tout en conservant les champs éditables
        try:
            acro = writer._root_object["/AcroForm"]
            if hasattr(acro, "get_object"):
                acro = acro.get_object()
            acro.update({NameObject("/NeedAppearances"): BooleanObject(True)})
        except Exception:
            pass

        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    except Exception as e:
        st.warning(f"Erreur lors du remplissage DC1 : {e}")
        return None


def generate_dc1_fallback(info: dict, project: dict) -> bytes:
    """
    Génère un PDF DC1 de substitution (sans template officiel)
    en recréant visuellement la structure du formulaire Cerfa 12156.
    Ce PDF est correctement structuré mais non interactif.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors as rl_colors

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        today = datetime.date.today().strftime("%d/%m/%Y")

        def draw_section(title, y_start):
            c.setFillColorRGB(0.93, 0.93, 0.93)
            c.rect(15*mm, y_start - 6*mm, w - 30*mm, 6*mm, fill=1, stroke=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(17*mm, y_start - 4.5*mm, title)
            return y_start - 10*mm

        def draw_field(label, value, x, y, label_w=50*mm, field_w=80*mm, line_h=6*mm):
            c.setFont("Helvetica", 7)
            c.setFillColorRGB(0.4, 0.4, 0.4)
            c.drawString(x, y, label)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica", 9)
            c.drawString(x + label_w, y, str(value))
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.line(x + label_w, y - 1*mm, x + label_w + field_w, y - 1*mm)
            return y - line_h

        # En-tête
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w/2, h - 20*mm, "DC1 — LETTRE DE CANDIDATURE")
        c.setFont("Helvetica", 8)
        c.drawCentredString(w/2, h - 25*mm, "Formulaire de candidature aux marchés publics — Cerfa 12156")
        c.setStrokeColorRGB(0, 0.33, 1)
        c.setLineWidth(1.5)
        c.line(15*mm, h - 27*mm, w - 15*mm, h - 27*mm)
        c.setLineWidth(0.5)

        y = h - 35*mm

        # Section A
        y = draw_section("A — POUVOIR ADJUDICATEUR", y)
        y = draw_field("Objet du marché :", project.get("name",""), 15*mm, y)
        y = draw_field("Référence :", "", 15*mm, y)
        y -= 3*mm

        # Section B
        y = draw_section("B — IDENTIFICATION DU CANDIDAT", y)
        y = draw_field("Dénomination sociale :", info.get("name",""), 15*mm, y)
        y = draw_field("Forme juridique :", info.get("forme_juridique",""), 15*mm, y)
        y = draw_field("Numéro SIRET :", info.get("siret",""), 15*mm, y)
        y = draw_field("Code APE/NAF :", info.get("ape",""), 15*mm, y)
        y = draw_field("Adresse :", info.get("address",""), 15*mm, y)
        y = draw_field("Ville :", info.get("city",""), 15*mm, y)
        y = draw_field("TVA intracommunautaire :", info.get("tva",""), 15*mm, y)
        y -= 3*mm

        # Section C — Chiffres d'affaires
        y = draw_section("C — CAPACITÉS ÉCONOMIQUES ET FINANCIÈRES", y)
        y = draw_field("Chiffre d'affaires N-1 :", f"{info.get('ca_n1',0):,.0f} €", 15*mm, y)
        y = draw_field("Chiffre d'affaires N-2 :", f"{info.get('ca_n2',0):,.0f} €", 15*mm, y)
        y = draw_field("Chiffre d'affaires N-3 :", f"{info.get('ca_n3',0):,.0f} €", 15*mm, y)
        y -= 3*mm

        # Section D — Signature
        y = draw_section("D — DÉCLARATION SUR L'HONNEUR ET SIGNATURE", y)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        disclaimer = (
            "Le candidat déclare sur l'honneur ne pas entrer dans l'un des cas d'exclusion "
            "de la procédure de passation des marchés publics prévus aux articles L.2141-1 "
            "à L.2141-14 du code de la commande publique."
        )
        text_obj = c.beginText(15*mm, y)
        text_obj.setFont("Helvetica", 8)
        # Wrap manuel
        words = disclaimer.split()
        line, lines = [], []
        for w_word in words:
            line.append(w_word)
            if c.stringWidth(" ".join(line), "Helvetica", 8) > (w - 30*mm):
                lines.append(" ".join(line[:-1]))
                line = [w_word]
        lines.append(" ".join(line))
        for ln in lines:
            text_obj.textLine(ln)
        c.drawText(text_obj)
        y -= (len(lines) + 1) * 5*mm

        y = draw_field("Fait à :", info.get("city",""), 15*mm, y)
        y = draw_field("Le :", today, 15*mm, y)
        y = draw_field("Nom & Prénom :", info.get("rep_legal",""), 15*mm, y)
        y = draw_field("Qualité :", info.get("qualite_signataire","Gérant"), 15*mm, y)

        # Zone signature
        y -= 5*mm
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.rect(15*mm, y - 20*mm, 70*mm, 20*mm, fill=0, stroke=1)
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawString(17*mm, y - 10*mm, "Signature et cachet de l'entreprise")

        # Pied de page
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(w/2, 10*mm,
            f"Document généré par Lexus Enterprise le {today} — "
            "Pour un DC1 officiel interactif, chargez le modèle gouvernemental dans Paramètres > CERFA"
        )

        c.save()
        return buf.getvalue()

    except ImportError:
        # Ultra-fallback si reportlab absent (ne devrait pas arriver sur Streamlit Cloud)
        raise RuntimeError("ReportLab non disponible. Installez-le via requirements.txt.")


def get_dc1_pdf(info: dict, project: dict) -> tuple[bytes, str]:
    """
    Point d'entrée unique pour la génération DC1.
    Retourne (bytes_pdf, mode_label).
    Priorité : 1) PDF officiel rempli  2) PDF de substitution
    """
    official = fill_dc1_official(info, project)
    if official:
        return official, "officiel"
    return generate_dc1_fallback(info, project), "substitution"


# ============================================================
# 7. MOTEUR IA — Claude (Anthropic)
# ============================================================

CLAUDE_MODEL = "claude-sonnet-4-6"

try:
    _api_key = st.secrets.get("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", None)
    if _api_key:
        _claude_client = anthropic.Anthropic(api_key=_api_key)
        API_STATUS = "ONLINE"
    else:
        _claude_client = None
        API_STATUS = "OFFLINE"
except Exception:
    _claude_client = None
    API_STATUS = "LOCAL"


def _pil_to_base64(image: Image.Image) -> tuple[str, str]:
    """Convertit une image PIL en base64 + media_type pour l'API Claude."""
    buf = io.BytesIO()
    fmt = image.format or "PNG"
    if fmt not in ("PNG", "JPEG", "GIF", "WEBP"):
        fmt = "PNG"
    image.save(buf, format=fmt)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    media_type = f"image/{fmt.lower()}"
    return b64, media_type


def analyze_and_update(image: Image.Image, context: str) -> tuple[dict | None, str]:
    """
    Analyse structurée d'un DCE : retourne un dict JSON + résumé.
    Utilisé pour le scoring automatique d'un projet.
    """
    if not _claude_client:
        return None, "Clé API ANTHROPIC_API_KEY manquante dans les secrets Streamlit."

    b64, media_type = _pil_to_base64(image)

    prompt = f"""Tu es un expert en marchés publics français. Contexte : {context}

Analyse ce document (DCE / CCTP / RC) et retourne UNIQUEMENT un objet JSON valide,
sans markdown, sans texte avant ni après :

{{
    "match": <entier 0-100 représentant le % de correspondance avec le profil>,
    "rse": "<Faible | Moyen | Fort> engagement RSE détecté",
    "delay": "<délai d'exécution ex: 6 mois>",
    "penalty": "<taux de pénalité ex: 1% par jour>",
    "summary": "<résumé détaillé en français : points clés, risques, opportunités>"
}}"""

    try:
        resp = _claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = resp.content[0].text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return data, data.get("summary", "")
    except json.JSONDecodeError:
        return None, "L'IA n'a pas renvoyé un JSON valide. Réessayez."
    except anthropic.AuthenticationError:
        return None, "Clé API invalide. Vérifiez ANTHROPIC_API_KEY dans vos secrets."
    except anthropic.RateLimitError:
        return None, "Quota API atteint. Attendez quelques instants."
    except Exception as e:
        return None, f"Erreur d'analyse : {e}"


def analyze(image: Image.Image, prompt: str) -> str:
    """
    Analyse libre (Studio IA) : retourne du texte formaté.
    Consomme 1 crédit par appel.
    """
    plan_info = PLANS.get(st.session_state.subscription_plan, PLANS["GRATUIT"])
    if st.session_state.credits_used >= plan_info["limit"]:
        return (
            f"⚠️ Limite de {plan_info['limit']} analyses/semaine atteinte. "
            "Passez à l'abonnement supérieur dans Paramètres › Abonnements."
        )
    if not _claude_client:
        return "⚠️ Clé API manquante. Ajoutez ANTHROPIC_API_KEY dans vos secrets Streamlit."

    b64, media_type = _pil_to_base64(image)

    try:
        resp = _claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        st.session_state.credits_used += 1
        return resp.content[0].text
    except anthropic.AuthenticationError:
        return " Clé API invalide. Vérifiez ANTHROPIC_API_KEY."
    except anthropic.RateLimitError:
        return " Quota API atteint. Attendez quelques instants puis réessayez."
    except Exception as e:
        return f"Erreur : {e}"


# ============================================================
# 8. LANDING / AUTH
# ============================================================
if not st.session_state.authenticated:

    if st.session_state.auth_view == "landing":
        c1, c2 = st.columns([2, 8])
        with c1:
            st.markdown(
                "<div style='padding-top:10px;'>"
                "<span class='lexus-logo-text'>L A</span>"
                "<span class='lexus-dot'>.</span></div>",
                unsafe_allow_html=True,
            )
        with c2:
            _, sc2 = st.columns([7, 2])
            if sc2.button("Se connecter", key="btn_login_home"):
                st.session_state.auth_view = "login"
                st.rerun()

        st.write(""); st.write(""); st.write("")
        st.markdown(
            "<div class='hero-title'>L'Intelligence Artificielle pour<br>"
            "<span style='color:#0055FF'>vos marchés publics.</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='hero-subtitle'>Centralisez vos appels d'offres. Analysez vos documents en un clic.<br>"
            "Générez vos dossiers administratifs sans erreur.</div>",
            unsafe_allow_html=True,
        )
        _, c_cta, _ = st.columns([1, 1, 1])
        with c_cta:
            with st.form("hero_cta"):
                if st.form_submit_button("CRÉER UN COMPTE GRATUIT"):
                    st.session_state.auth_view = "signup"
                    st.rerun()
            st.markdown(
                "<div style='text-align:center;font-size:12px;color:#888;margin-top:10px;'>"
                "Accès immédiat • Paiement à la consommation IA</div>",
                unsafe_allow_html=True,
            )

        st.write(""); st.write("")
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            st.markdown("""<div class="feature-card">
<div class="feature-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
<polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></div>
<div class="feature-title">Analyse Sémantique</div>
<div class="feature-desc">Notre IA lit et comprend vos cahiers des charges. Elle extrait instantanément les critères et délais.</div>
</div>""", unsafe_allow_html=True)
        with cf2:
            st.markdown("""<div class="feature-card">
<div class="feature-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
</svg></div>
<div class="feature-title">Gestion Administrative</div>
<div class="feature-desc">Fini la saisie manuelle. Lexus pré-remplit vos DC1, DC2 et documents de conformité.</div>
</div>""", unsafe_allow_html=True)
        with cf3:
            st.markdown("""<div class="feature-card">
<div class="feature-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>
</svg></div>
<div class="feature-title">Pilotage Financier</div>
<div class="feature-desc">Un tableau de bord clair pour suivre vos taux de succès et votre CA prévisionnel.</div>
</div>""", unsafe_allow_html=True)

        st.write("")
        st.markdown("<hr style='border:0;border-top:1px solid #eee;margin:50px 0;'>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;color:#888;font-size:12px;'>© 2026 LEXUS Enterprise.</div>",
            unsafe_allow_html=True,
        )

    elif st.session_state.auth_view in ["login", "signup"]:
        _, c2, _ = st.columns([1, 1, 1])
        with c2:
            st.markdown(
                "<br><br><div style='text-align:center;margin-bottom:20px;'>"
                "<span class='lexus-logo-text'>L A</span><span class='lexus-dot'>.</span></div>",
                unsafe_allow_html=True,
            )
            mode = "Se connecter" if st.session_state.auth_view == "login" else "Créer un compte"
            st.markdown(f"<h3 style='text-align:center;margin-bottom:30px;'>{mode}</h3>", unsafe_allow_html=True)
            with st.form("auth_form"):
                username = st.text_input("Identifiant / Email")
                password = st.text_input("Mot de passe", type="password")
                if mode == "Créer un compte":
                    st.text_input("Nom de l'entreprise")
                if st.form_submit_button("SE CONNECTER" if mode == "Se connecter" else "S'INSCRIRE"):
                    current_db = get_db()
                    if mode == "Créer un compte":
                        if username in current_db:
                            st.error("Cet identifiant existe déjà.")
                        else:
                            save_user(username, {"password": password, "role": "user",
                                                 "plan": "GRATUIT", "email": username})
                            st.success("Compte créé !")
                            time.sleep(1)
                            st.session_state.auth_view = "login"
                            st.rerun()
                    else:
                        if username in current_db and current_db[username]["password"] == password:
                            st.session_state.authenticated = True
                            st.session_state.user_name = username
                            st.session_state.user_role = current_db[username].get("role", "user")
                            user_plan = current_db[username].get("plan", "GRATUIT")
                            st.session_state.subscription_plan = user_plan
                            st.session_state.credits_limit = PLANS[user_plan]["limit"]
                            st.rerun()
                        else:
                            st.error("Identifiants incorrects.")
            if st.button("← Retour"):
                st.session_state.auth_view = "landing"
                st.rerun()

    st.stop()


# ============================================================
# 9. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
<div style='margin-bottom:40px;padding-left:5px;'>
<span class='lexus-logo-text'>L</span><span style='color:#aaa;font-weight:200;font-size:26px;'>A</span>
<span class='lexus-dot'>.</span>
<div style='font-size:10px;letter-spacing:3px;font-weight:700;margin-top:5px;color:#444;'>LEXUS AI</div>
</div>""", unsafe_allow_html=True)

    nav_items = [
        ("dashboard", "Tableau de bord"),
        ("studio",    "Lexus AI Studio"),
        ("settings",  "Paramètres"),
    ]
    for page_key, label in nav_items:
        if st.button(label, key=f"nav_{page_key}"):
            st.session_state.page = page_key
            st.rerun()

    if st.session_state.get("user_role") == "admin":
        st.markdown("---")
        if st.button(" ADMIN PANEL"):
            st.session_state.page = "admin"
            st.rerun()

    st.markdown("---")

    # Crédits restants
    plan = st.session_state.subscription_plan
    used = st.session_state.credits_used
    limit = PLANS[plan]["limit"]
    remaining = max(0, limit - used)
    pct = min(100, int(used / max(limit, 1) * 100))
    st.markdown(
        f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>CRÉDITS IA — {plan}</div>"
        f"<div style='font-size:13px;font-weight:600;color:#111;'>{remaining} restants</div>",
        unsafe_allow_html=True,
    )
    st.progress(pct / 100)
    st.markdown("---")

    if st.button("Déconnexion"):
        st.session_state.authenticated = False
        st.session_state.auth_view = "landing"
        st.rerun()

    status_color = "#00C853" if API_STATUS == "ONLINE" else "#FF0000"
    st.markdown(
        f"<div style='font-size:10px;color:#999;margin-top:10px;'>SERVEUR : "
        f"<span style='color:{status_color};font-weight:bold;'>{API_STATUS}</span></div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 10. PAGES
# ============================================================

# ── DASHBOARD ──────────────────────────────────────────────
if st.session_state.page == "dashboard":
    st.markdown(
        f"## Espace <span style='color:#0055FF'>{st.session_state.company_info['name']}</span>",
        unsafe_allow_html=True,
    )

    projects = st.session_state.projects
    total = sum(p["budget"] for p in projects)
    nb = len(projects)
    avg = total / nb if nb else 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='kpi-card'><div class='kpi-label'>CA PIPELINE</div><div class='kpi-value'>{total:,.0f} €</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><div class='kpi-label'>BUDGET MOYEN</div><div class='kpi-value'>{avg:,.0f} €</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><div class='kpi-label'>DOSSIERS ACTIFS</div><div class='kpi-value'>{nb}</div></div>", unsafe_allow_html=True)

    st.write(""); st.caption("APPELS D'OFFRES / DOSSIERS")

    if not projects:
        st.info("Aucun dossier en cours. Ajoutez votre premier appel d'offres ci-dessous.")
    else:
        for p in projects:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.markdown(
                    f"**{p['name']}**<br><span style='color:#888;font-size:12px;'>{p['client']}</span>",
                    unsafe_allow_html=True,
                )
                col2.markdown(f"<span style='color:#0055FF;font-weight:bold;'>{p['budget']:,.0f} €</span>", unsafe_allow_html=True)
                if col3.button("Ouvrir", key=f"open_{p['id']}"):
                    st.session_state.current_project = p
                    st.session_state.page = "project"
                    st.rerun()
                st.markdown("<hr style='margin:10px 0;border-color:#eee;'>", unsafe_allow_html=True)

    with st.expander("Ajouter un nouvel appel d'offres +"):
        with st.form("new_ao"):
            col_a, col_b = st.columns(2)
            n_name   = col_a.text_input("Nom du marché")
            n_client = col_b.text_input("Acheteur / Client")
            n_budget = st.number_input("Budget estimé (€)", min_value=0, value=0, step=1000)
            if st.form_submit_button("Créer le dossier"):
                st.session_state.projects.append({
                    "id":            len(projects) + 1,
                    "name":          n_name,
                    "client":        n_client,
                    "budget":        n_budget,
                    "status":        "NOUVEAU",
                    "analysis_done": False,
                    "match": 0, "rse": "-", "delay": "-", "penalty": "-",
                })
                st.rerun()


# ── DÉTAIL PROJET ───────────────────────────────────────────
elif st.session_state.page == "project":
    p = st.session_state.current_project
    if not p:
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("← Retour à la liste"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.title(p["name"])
    st.caption(f"Client : {p['client']} • Budget : {p['budget']:,.0f} €")

    col_left, col_right = st.columns([1, 1], gap="large")

    # FLUX DE TRAVAIL
    with col_left:
        st.subheader("Flux de Travail")
        steps = [
            " Prise de contact",
            " Réunion équipe",
            " Collecte documents",
            " Estimation devis",
            "  Rédaction mémoire",
            " Relecture",
            " Documents administratifs",
            " Envoi du dossier",
            " Réception accusé",
            " Compléments éventuels",
            " Relance / Résultat",
        ]
        for step in steps:
            st.checkbox(step, key=f"w_{p['id']}_{step}")

    # ANALYSE IA + DC1
    with col_right:
        st.subheader("Analyse du Dossier")
        uploaded_file = st.file_uploader("Importer le DCE (image)", type=["png", "jpg", "jpeg"])

        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption="Document chargé", width=200)
            if st.button("LANCER L'ANALYSE IA"):
                with st.spinner("Analyse en cours..."):
                    criteria_text = (
                        f"Compétences requises: {', '.join(st.session_state.user_criteria['skills'])}. "
                        f"CA min requis: {st.session_state.user_criteria['min_turnover_required']}€. "
                        f"Pénalités max acceptées: {st.session_state.user_criteria['max_penalties']}%."
                    )
                    data, summary = analyze_and_update(img, f"Projet: {p['name']}. {criteria_text}")
                    if data:
                        p.update({
                            "analysis_done": True,
                            "match":   data.get("match", 0),
                            "rse":     data.get("rse", "Inconnu"),
                            "delay":   data.get("delay", "Inconnu"),
                            "penalty": data.get("penalty", "Inconnu"),
                        })
                        st.session_state[f"res_{p['id']}"] = summary
                        st.rerun()
                    else:
                        st.error(summary)

        if p.get("analysis_done"):
            st.success(" Analyse terminée")
            r1, r2, r3, r4 = st.columns(4)
            r1.markdown(f"<div class='result-card'><div class='result-label'>MATCHING</div><div class='result-value'>{p.get('match','-')}%</div></div>", unsafe_allow_html=True)
            r2.markdown(f"<div class='result-card'><div class='result-label'>RSE</div><div class='result-value'>{p.get('rse','-')}</div></div>", unsafe_allow_html=True)
            r3.markdown(f"<div class='result-card'><div class='result-label'>DÉLAI</div><div class='result-value'>{p.get('delay','-')}</div></div>", unsafe_allow_html=True)
            r4.markdown(f"<div class='result-card'><div class='result-label'>PÉNALITÉS</div><div class='result-value'>{p.get('penalty','-')}</div></div>", unsafe_allow_html=True)

            with st.expander(" Compte Rendu Détaillé", expanded=True):
                if f"res_{p['id']}" in st.session_state:
                    st.write(st.session_state[f"res_{p['id']}"])

            st.divider()
            st.subheader("Documents Administratifs")

            # ── DC1 : génération intelligente ──────────────────
            dc1_available = (
                os.path.exists(DC1_LOCAL_PATH)
                and os.path.getsize(DC1_LOCAL_PATH) > 10_000
            )

            if dc1_available:
                st.markdown(
                    "<div class='dc1-status dc1-ok'>"
                    " <strong>Modèle DC1 officiel chargé</strong> — "
                    "Le PDF généré sera le formulaire gouvernemental pré-rempli et modifiable."
                    "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='dc1-status dc1-warn'>"
                    " <strong>Modèle DC1 officiel non disponible</strong> — "
                    "Un PDF de substitution sera généré. "
                    "Pour obtenir le formulaire officiel, chargez-le dans <em>Paramètres › CERFA</em>."
                    "</div>",
                    unsafe_allow_html=True,
                )

            if st.button("📄 Générer le DC1"):
                with st.spinner("Génération du DC1..."):
                    try:
                        pdf_bytes, mode = get_dc1_pdf(st.session_state.company_info, p)
                        label = (
                            " Télécharger le DC1 officiel (PDF modifiable)"
                            if mode == "officiel"
                            else " Télécharger le DC1 (PDF de substitution)"
                        )
                        st.download_button(
                            label=label,
                            data=pdf_bytes,
                            file_name=f"DC1_{p['name'].replace(' ','_')}.pdf",
                            mime="application/pdf",
                        )
                        if mode == "officiel":
                            st.success(" Formulaire DC1 officiel pré-rempli. Les champs restent modifiables dans votre lecteur PDF.")
                        else:
                            st.info("PDF de substitution généré. Chargez le modèle officiel pour obtenir le Cerfa interactif.")
                    except Exception as e:
                        st.error(f"Erreur lors de la génération : {e}")

            # Zone d'upload du modèle officiel
            with st.expander("⚙️ Charger / Remplacer le modèle DC1 officiel"):
                st.markdown(
                    "Téléchargez le formulaire DC1 depuis "
                    "[economie.gouv.fr](https://www.economie.gouv.fr/daj/formulaires-dc) "
                    "puis chargez-le ici. Il sera stocké et utilisé pour toutes vos candidatures."
                )
                model_upload = st.file_uploader("Formulaire DC1 officiel (.pdf)", type=["pdf"])
                if model_upload:
                    raw = model_upload.read()
                    # Vérification basique : le PDF doit avoir des champs AcroForm
                    try:
                        reader_check = PdfReader(io.BytesIO(raw))
                        fields_check = reader_check.get_fields()
                        nb_fields = len(fields_check) if fields_check else 0
                    except Exception:
                        nb_fields = 0

                    with open(DC1_LOCAL_PATH, "wb") as f:
                        f.write(raw)
                    st.session_state.dc1_download_tried = False  # reset pour retry

                    if nb_fields > 0:
                        st.success(f" Modèle chargé avec succès ({nb_fields} champs interactifs détectés). Générez le DC1 ci-dessus.")
                        with st.expander("🔍 Voir les champs détectés"):
                            st.json(list(fields_check.keys()))
                    else:
                        st.warning(
                            " Ce PDF ne semble pas contenir de champs interactifs AcroForm. "
                            "Assurez-vous de charger le formulaire officiel (pas une version scannée)."
                        )


# ── STUDIO IA ───────────────────────────────────────────────
elif st.session_state.page == "studio":
    st.title("Lexus AI Studio")

    if st.session_state.studio_mode is None:
        c1, c2, c3 = st.columns(3)
        modes = [
            ("AO",        "Analyse AO",   "Extraction critères, scoring, risques", "s1"),
            ("Finance",   "Finance",       "Devis, factures, analyse budgétaire",   "s2"),
            ("Juridique", "Juridique",     "Risques contractuels & conformité",     "s3"),
        ]
        for col, (mode_key, title, desc, btn_key) in zip([c1, c2, c3], modes):
            with col:
                st.markdown(f"""<div class="studio-btn">
<div class="studio-t">{title}</div>
<div class="studio-d">{desc}</div>
</div>""", unsafe_allow_html=True)
                if st.button("Lancer", key=btn_key):
                    st.session_state.studio_mode = mode_key
                    st.rerun()
    else:
        if st.button("← Retour"):
            st.session_state.studio_mode = None
            st.rerun()

        mode = st.session_state.studio_mode
        st.markdown(f"### Mode : {mode}")

        prompts = {
            "AO": (
                "Tu es expert en marchés publics français. Analyse ce document (DCE/CCTP/RC) et extrais : "
                "critères d'attribution et pondérations, délai d'exécution, pénalités de retard, "
                "exigences RSE/développement durable, garanties demandées, niveau de complexité administrative. "
                "Présente une synthèse structurée avec recommandations."
            ),
            "Finance": (
                "Tu es expert-comptable spécialisé marchés publics. Analyse ce document financier et fournis : "
                "synthèse des montants et postes budgétaires, détection d'anomalies, "
                "ratios financiers clés, recommandations d'optimisation."
            ),
            "Juridique": (
                "Tu es juriste spécialisé en droit de la commande publique. Analyse ce document et identifie : "
                "clauses à risque pour le titulaire, obligations particulières, "
                "points de vigilance CCAG, risques de litiges potentiels."
            ),
        }

        f = st.file_uploader("Document à analyser", type=["png", "jpg", "jpeg"])
        if f:
            im = Image.open(f)
            st.image(im, width=200)
            if st.button("ANALYSER"):
                with st.spinner("Analyse en cours..."):
                    result = analyze(im, prompts.get(mode, f"Analyse mode {mode}"))
                    st.markdown(result)


# ── ADMIN ────────────────────────────────────────────────────
elif st.session_state.page == "admin":
    if st.session_state.get("user_role") != "admin":
        st.error("Accès refusé.")
        st.stop()

    st.title("Console Administration")
    current_db = get_db()
    users_data = [
        {"Utilisateur": u, "Email": d.get("email",""), "Plan": d.get("plan",""), "Rôle": d.get("role","")}
        for u, d in current_db.items()
    ]
    st.dataframe(pd.DataFrame(users_data), use_container_width=True)

    st.divider()
    col_a, col_b, col_c = st.columns(3)
    target_user = col_a.selectbox("Utilisateur", list(current_db.keys()))
    target_plan = col_b.selectbox("Nouveau plan", ["GRATUIT", "PRO", "ULTRA"])
    col_c.write("")
    col_c.write("")
    if col_c.button("Mettre à jour"):
        update_plan(target_user, target_plan)
        st.success(f"Plan de {target_user} mis à jour → {target_plan}")
        time.sleep(1)
        st.rerun()


# ── PARAMÈTRES ───────────────────────────────────────────────
elif st.session_state.page == "settings":
    st.title("Paramètres Généraux")

    t1, t2, t3, t4 = st.tabs([" Critères", " Abonnements", " Mentions", " CERFA"])

    # TAB 1 — CRITÈRES
    with t1:
        st.subheader("Compétences")
        c_add, c_btn = st.columns([3, 1])
        new_skill = c_add.text_input("Nouvelle compétence", label_visibility="collapsed", placeholder="Ex: Informatique, BTP, Nettoyage…")
        if c_btn.button("AJOUTER"):
            if new_skill and new_skill not in st.session_state.user_skills:
                st.session_state.user_skills.append(new_skill)
                st.rerun()

        tags_html = "".join(f"<span class='skill-tag'>{s}</span>" for s in st.session_state.user_skills)
        st.markdown(tags_html or "<span style='color:#aaa'>Aucune compétence ajoutée</span>", unsafe_allow_html=True)

        if st.session_state.user_skills and st.button("Effacer tout"):
            st.session_state.user_skills = []
            st.rerun()

        st.divider()
        st.subheader("Filtres Financiers & Contractuels")
        c1, c2 = st.columns(2)
        st.session_state.user_criteria["min_daily_rate"] = c1.number_input(
            "Taux Journalier Minimum (€)", value=st.session_state.user_criteria["min_daily_rate"]
        )
        st.session_state.user_criteria["max_penalties"] = c2.slider(
            "Pénalités max acceptées (%)", 0, 20, st.session_state.user_criteria["max_penalties"]
        )
        st.session_state.user_criteria["min_turnover_required"] = c1.number_input(
            "CA minimum exigé par les AO (€)", value=st.session_state.user_criteria["min_turnover_required"], step=10000
        )
        st.session_state.user_criteria["max_distance"] = c2.number_input(
            "Distance max chantier (km)", value=st.session_state.user_criteria["max_distance"]
        )

    # TAB 2 — ABONNEMENTS
    with t2:
        st.subheader("Plans Tarifaires")
        cols = st.columns(3)
        for i, (plan_key, plan_data) in enumerate(PLANS.items()):
            with cols[i]:
                is_current = st.session_state.subscription_plan == plan_key
                border = "border:2px solid #0055FF;" if is_current else ""
                st.markdown(f"""<div class="price-col" style="{border}">
<div class="price-tag">{plan_data['label']}</div>
<div class="price-amount">{plan_data['price']}<span style='font-size:14px;font-weight:400;color:#888;'>/mois</span></div>
<ul class="price-list">
  <li>✅ {plan_data['limit'] if plan_data['limit'] < 9999 else '∞'} analyses / semaine</li>
  <li>{'✅' if plan_key != 'GRATUIT' else '❌'} DC1 officiel illimité</li>
  <li>{'✅' if plan_key == 'ULTRA' else '❌'} Support prioritaire</li>
</ul>
</div>""", unsafe_allow_html=True)
                if is_current:
                    st.button("Plan actuel", key=f"plan_{plan_key}", disabled=True)
                elif plan_data["link"]:
                    st.link_button("Choisir ce plan", plan_data["link"])

    # TAB 3 — MENTIONS
    with t3:
        st.subheader("Mentions Légales")
        st.text_area("Contenu des mentions légales", height=150, placeholder="Entrez vos mentions légales ici…")

    # TAB 4 — CERFA / INFOS ENTREPRISE
    with t4:
        st.subheader("Informations Entreprise (pré-remplissage DC1/DC2)")
        with st.form("cerfa_form"):
            info = st.session_state.company_info

            st.markdown("##### Identification")
            c1, c2 = st.columns(2)
            info["name"]          = c1.text_input("Dénomination sociale", value=info.get("name",""))
            info["forme_juridique"] = c2.text_input("Forme juridique", value=info.get("forme_juridique",""), placeholder="SAS, SARL, EI…")
            info["siret"]         = c1.text_input("Numéro SIRET (14 chiffres)", value=info.get("siret",""))
            info["ape"]           = c2.text_input("Code APE/NAF", value=info.get("ape",""))
            info["tva"]           = c1.text_input("N° TVA intracommunautaire", value=info.get("tva",""))
            info["capital"]       = c2.number_input("Capital social (€)", value=int(info.get("capital",0)), step=1000)

            st.markdown("##### Coordonnées")
            c3, c4 = st.columns(2)
            info["address"]       = c3.text_input("Adresse (rue)", value=info.get("address",""))
            info["code_postal"]   = c4.text_input("Code postal", value=info.get("code_postal",""))
            info["city"]          = c3.text_input("Ville", value=info.get("city",""))

            st.markdown("##### Représentant légal")
            c5, c6 = st.columns(2)
            info["rep_legal"]             = c5.text_input("Nom & Prénom", value=info.get("rep_legal",""))
            info["qualite_signataire"]     = c6.text_input("Qualité (fonction)", value=info.get("qualite_signataire","Gérant"))

            st.markdown("##### Chiffres d'affaires")
            c7, c8, c9 = st.columns(3)
            info["ca_n1"] = c7.number_input("CA N-1 (€)", value=int(info.get("ca_n1",0)), step=10000)
            info["ca_n2"] = c8.number_input("CA N-2 (€)", value=int(info.get("ca_n2",0)), step=10000)
            info["ca_n3"] = c9.number_input("CA N-3 (€)", value=int(info.get("ca_n3",0)), step=10000)

            if st.form_submit_button(" SAUVEGARDER"):
                st.session_state.company_info = info
                st.success("✅ Informations sauvegardées avec succès.")
