"""Tiny i18n for the hub dashboard: English + Kinyarwanda.

The Kinyarwanda ('rw') strings are a DRAFT (consistent with the USSD/SMS
scripts). Mimi should check and correct them before use, like the other
Kinyarwanda in the repo. Diagnosis names are loaded from hub/sms_script.json
so they stay in one place.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# languages offered in the toggle (code, label-in-its-own-language)
LANGS = [("en", "English"), ("rw", "Ikinyarwanda")]
DEFAULT_LANG = "en"

UI = {
    "en": {
        "hub_tag": "offline · coop washing station",
        "footer": "Synthetic data for a hackathon prototype. Numbers reuse "
                  "<code>shared/</code>, so they match the SMS loop and tests.",
        # index
        "page_title_index": "FarmFlow hub — all farmers",
        "hero_eyebrow": "FarmFlow · Season {season} harvest",
        "hero_title_a": "Cooperative",
        "hero_title_b": "overview",
        "hero_sub": "{farmers} farmers across {coops} cooperatives, their deliveries, "
                    "forecasts and the credit waiting on a coop-staff approval.",
        "credit_pending": "Credit pending approval",
        "feature_note": "Proposed across all cooperatives, each waiting for a coop "
                        "staff member to reply “OK”.",
        "stat_farmers": "Farmers",
        "stat_trees": "Coffee trees",
        "stat_cherry_season": "Cherry delivered, {season} (kg)",
        "stat_cherry_all": "Cherry all-time (kg)",
        "sec_coops": "Cooperatives",
        "sec_farmers": "Farmers",
        "coop_meta": "{district} district · {farmers} farmers · {price} RWF/kg ({season})",
        "coop_kg_season": "kg this season",
        "coop_trees": "trees",
        "coop_pending": "RWF pending",
        "search_ph": "Search farmer, id or village…",
        "demo_only": "Demo farmers only",
        "shown": "shown",
        "th_farmer": "Farmer", "th_coop": "Coop", "th_village": "Village",
        "th_trees": "Trees", "th_season_kg": "{season} kg", "th_all_kg": "All-time kg",
        "th_seasons": "Seasons", "th_forecast": "Forecast P50", "th_credit": "Credit (RWF)",
        "th_status": "Status", "th_issue": "Latest issue", "th_action": "Action",
        "diagnose": "Diagnose", "analyzing": "Analyzing…",
        "status_pending_approval": "Pending approval",
        "status_insufficient_history": "New member",
        "status_approved": "Approved",
        # farmer page
        "back_all": "← All farmers",
        "farmer_meta": "{id} · {coop} ({district}) · {village} · {trees} trees · member since {since}",
        "panel_deliveries": "Cherry delivered by season (kg)",
        "no_deliveries": "No deliveries recorded yet.",
        "panel_forecast": "Harvest forecast — season {season}",
        "fc_low": "Low (P10)", "fc_exp": "Expected (P50)", "fc_high": "High (P90)",
        "fc_hist": "Seasons of history",
        "fc_thin": "{n} season(s) of history — too thin to forecast.",
        "panel_credit": "Proposed input credit",
        "credit_status": "Status", "credit_price": "First-payment price",
        "credit_outstanding": "Outstanding", "credit_approved_by": "Approved by",
        "credit_computed": "Computed at", "credit_model": "Model",
        "panel_diagnoses": "Diagnoses", "no_diagnoses": "No confirmed diagnoses.",
        "unit_kg": "kg", "unit_rwf": "RWF", "unit_rwf_kg": "RWF/kg",
        # diagnosis review
        "review_title": "Review leaf diagnosis", "review_farmer": "Farmer:",
        "retake_title": "Photo needs to be retaken",
        "too_dark": "The photo is too dark.", "too_blurry": "The photo is too blurry.",
        "bad_photo": "The photo could not be analyzed reliably.",
        "back_dash": "Back to dashboard",
        "notsure_label": "Not sure", "notsure_title": "Ask the coop team",
        "notsure_body": "FarmFlow isn’t confident enough to diagnose this leaf, so it "
                        "won’t suggest a treatment or credit. Please keep the leaves and "
                        "ask the coop team — or the extension officer — to take a look.",
        "closest_guess": "Closest guess: {cls} ({pct}%), below the confidence threshold.",
        "ai_diagnosis": "AI diagnosis", "confidence": "Confidence:",
        "model_class": "Model class: {cls}",
        "confirm": "Confirm diagnosis", "cancel": "Cancel",
    },
    "rw": {
        "hub_tag": "nta interineti · ku kigo cy'ikawa",
        "footer": "Amakuru y'icyitegererezo ya hackathon. Imibare ikoresha "
                  "<code>shared/</code>, bihuye na SMS na tests.",
        # index
        "page_title_index": "FarmFlow hub — abahinzi bose",
        "hero_eyebrow": "FarmFlow · Igihembwe {season} cy'isarura",
        "hero_title_a": "Incamake ya",
        "hero_title_b": "koperative",
        "hero_sub": "Abahinzi {farmers} muri koperative {coops}, ibyo batanze, iteganya "
                    "n'inguzanyo itegereje kwemezwa n'umukozi wa koperative.",
        "credit_pending": "Inguzanyo itegereje kwemezwa",
        "feature_note": "Yateganyijwe muri koperative zose, buri imwe itegereje umukozi "
                        "wa koperative kwandika “OK”.",
        "stat_farmers": "Abahinzi",
        "stat_trees": "Ibiti by'ikawa",
        "stat_cherry_season": "Ikawa yatanzwe, {season} (kg)",
        "stat_cherry_all": "Ikawa yose yatanzwe (kg)",
        "sec_coops": "Koperative",
        "sec_farmers": "Abahinzi",
        "coop_meta": "Akarere {district} · abahinzi {farmers} · {price} RWF/kg ({season})",
        "coop_kg_season": "kg iki gihembwe",
        "coop_trees": "ibiti",
        "coop_pending": "RWF itegereje",
        "search_ph": "Shakisha umuhinzi, ID cyangwa umudugudu…",
        "demo_only": "Abahinzi b'icyitegererezo gusa",
        "shown": "byerekanwe",
        "th_farmer": "Umuhinzi", "th_coop": "Koperative", "th_village": "Umudugudu",
        "th_trees": "Ibiti", "th_season_kg": "{season} kg", "th_all_kg": "kg yose",
        "th_seasons": "Ibihembwe", "th_forecast": "Iteganya P50", "th_credit": "Inguzanyo (RWF)",
        "th_status": "Uko bimeze", "th_issue": "Ikibazo giheruka", "th_action": "Igikorwa",
        "diagnose": "Suzuma", "analyzing": "Birasuzumwa…",
        "status_pending_approval": "Itegereje kwemezwa",
        "status_insufficient_history": "Umunyamuryango mushya",
        "status_approved": "Yemejwe",
        # farmer page
        "back_all": "← Abahinzi bose",
        "farmer_meta": "{id} · {coop} ({district}) · {village} · ibiti {trees} · umunyamuryango kuva {since}",
        "panel_deliveries": "Ikawa yatanzwe buri gihembwe (kg)",
        "no_deliveries": "Nta kawa yatanzwe irabonetse.",
        "panel_forecast": "Iteganya ry'isarura — igihembwe {season}",
        "fc_low": "Hasi (P10)", "fc_exp": "Biteganyijwe (P50)", "fc_high": "Hejuru (P90)",
        "fc_hist": "Ibihembwe by'amateka",
        "fc_thin": "Ibihembwe {n} gusa — ni bike ku iteganya.",
        "panel_credit": "Inguzanyo y'inyongeramusaruro yateganyijwe",
        "credit_status": "Uko bimeze", "credit_price": "Igiciro cy'ubwishyu bwa mbere",
        "credit_outstanding": "Umwenda usigaye", "credit_approved_by": "Yemejwe na",
        "credit_computed": "Yabazwe", "credit_model": "Moderi",
        "panel_diagnoses": "Indwara zasuzumwe", "no_diagnoses": "Nta ndwara yemejwe.",
        "unit_kg": "kg", "unit_rwf": "RWF", "unit_rwf_kg": "RWF/kg",
        # diagnosis review
        "review_title": "Suzuma indwara y'amababi", "review_farmer": "Umuhinzi:",
        "retake_title": "Ongera ufate ifoto",
        "too_dark": "Ifoto irijimye cyane.", "too_blurry": "Ifoto ntiyumvikana neza.",
        "bad_photo": "Ifoto ntishobora gusuzumwa neza.",
        "back_dash": "Subira ku rubuga",
        "notsure_label": "Ntibizwi neza", "notsure_title": "Baza itsinda rya koperative",
        "notsure_body": "FarmFlow ntifite icyizere gihagije cyo gusuzuma iri babi, bityo "
                        "ntizatanga umuti cyangwa inguzanyo. Bika amababi usabe itsinda rya "
                        "koperative — cyangwa umujyanama w'ubuhinzi — kubireba.",
        "closest_guess": "Igitekerezo cya hafi: {cls} ({pct}%), kiri munsi y'urwego rw'icyizere.",
        "ai_diagnosis": "Isuzuma rya AI", "confidence": "Icyizere:",
        "model_class": "Icyiciro cya moderi: {cls}",
        "confirm": "Emeza isuzuma", "cancel": "Hagarika",
    },
}

# diagnosis display names (en/rw) — single source in sms_script.json
try:
    _SMS = json.loads((HERE / "sms_script.json").read_text(encoding="utf-8"))
    DIAG_NAMES = _SMS.get("diagnosis_names", {})
except Exception:
    DIAG_NAMES = {}


def make_t(lang):
    base = UI.get(lang, UI[DEFAULT_LANG])
    fallback = UI[DEFAULT_LANG]

    def t(key):
        return base.get(key, fallback.get(key, key))

    return t


def diag_label(code, lang):
    """Human diagnosis name in the chosen language, or an em-dash if empty."""
    if not code:
        return "—"
    entry = DIAG_NAMES.get(code)
    if entry:
        return entry.get(lang) or entry.get("en") or code
    return code.replace("_", " ")
