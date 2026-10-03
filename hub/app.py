"""FarmFlow hub dashboard — read-only aggregate of every farmer and what they deliver.

Runs offline on the coop phone (Termux) or any laptop:

    pip install flask
    python hub/app.py            # then open http://127.0.0.1:5000

Reuses shared/ for every number, so the dashboard, the SMS loop and the tests agree.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # repo root, so `import shared` works
sys.path.insert(0, str(HERE))          # so `import dashboard` works

from flask import Flask, abort, render_template, request

import dashboard

app = Flask(__name__)

_CACHE = {}


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
    return render_template("farmer.html", f=row, season=row["limit"]["season"] - 1)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
