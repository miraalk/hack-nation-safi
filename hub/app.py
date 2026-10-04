"""FarmFlow hub dashboard — read-only aggregate of every farmer and what they deliver.

Runs offline on the coop phone (Termux) or any laptop:

    pip install flask
    python hub/app.py

Reuses shared/ for every number, so the dashboard, the SMS loop and the tests agree.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(ROOT))  # import shared / backend
sys.path.insert(0, str(HERE))  # import dashboard

from flask import Flask, abort, render_template, request

import dashboard
from i18n import UI, DEFAULT_LANG, LANGS, make_t, diag_label
from backend.routes.sms_webhook import sms_bp
from backend.routes.ussd_webhook import ussd_bp
from backend.routes.vision import vision_bp
app = Flask(__name__)

# Africa's Talking webhook routes
app.register_blueprint(sms_bp)
app.register_blueprint(ussd_bp)
app.register_blueprint(vision_bp)
_CACHE = {}


def _current_lang():
    """Language from ?lang=, else the saved cookie, else English."""
    lang = request.args.get("lang") or request.cookies.get("lang") or DEFAULT_LANG
    return lang if lang in UI else DEFAULT_LANG


@app.context_processor
def _inject_i18n():
    lang = _current_lang()
    return {
        "lang": lang,
        "langs": LANGS,
        "t": make_t(lang),
        "diag": lambda code: diag_label(code, lang),
    }


@app.after_request
def _persist_lang(response):
    chosen = request.args.get("lang")
    if chosen in UI:
        response.set_cookie("lang", chosen, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def _data(reload=False):
    """Aggregates are a little expensive over all farmers, so cache until reload."""
    if reload or "data" not in _CACHE:
        _CACHE["data"] = dashboard.build()

    return _CACHE["data"]


@app.template_filter("rwf")
def _rwf(value):
    return f"{int(value or 0):,}"


@app.template_filter("kg")
def _kg(value):
    if value is None:
        return "—"

    return f"{int(round(value)):,}"


@app.route("/")
def index():
    data = _data(reload=request.args.get("reload") == "1")
    return render_template("index.html", **data)


@app.route("/farmer/<farmer_id>")
def farmer(farmer_id):
    row = dashboard.farmer(farmer_id)

    if row is None:
        abort(404)

    return render_template(
        "farmer.html",
        f=row,
        season=row["limit"]["season"] - 1,
    )


if __name__ == "__main__":
    # Hosts (Railway, etc.) inject the port to bind on via $PORT.
    port = int(os.environ.get("PORT", 5001))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )