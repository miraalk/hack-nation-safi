import sqlite3
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, redirect, render_template, request
from werkzeug.utils import secure_filename

from shared.data import load_farmers


vision_bp = Blueprint("vision", __name__)

ROOT = Path(__file__).resolve().parents[2]

UPLOAD_DIR = ROOT / "data" / "leaf_images"
DB_PATH = ROOT / "data" / "farmflow.db"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


# ---------------------------------------------------------
# Lazy-loaded vision model
# ---------------------------------------------------------

_model = None


def get_model():
    global _model

    if _model is None:
        start = time.perf_counter()

        print("Loading vision dependencies...")

        # IMPORTANT:
        # Import Ultralytics/LeafModel only when vision
        # is actually requested.
        from vision.predict import LeafModel

        print(
            f"Vision dependencies imported in "
            f"{time.perf_counter() - start:.3f}s"
        )

        model_start = time.perf_counter()

        print("Loading vision model...")

        _model = LeafModel()

        print(
            f"Vision model ready in "
            f"{time.perf_counter() - model_start:.3f}s"
        )

    return _model


# ---------------------------------------------------------
# Run diagnosis
# ---------------------------------------------------------

@vision_bp.post("/diagnose")
def diagnose():
    total_start = time.perf_counter()

    farmer_id = request.form.get(
        "farmer_id",
        "",
    ).strip().upper()

    image = request.files.get(
        "image"
    )

    if not farmer_id:
        return "Missing farmer_id", 400

    farmers_start = time.perf_counter()

    farmers = load_farmers()

    print(
        f"load_farmers: "
        f"{time.perf_counter() - farmers_start:.3f}s"
    )

    if farmer_id not in farmers:
        return "Unknown farmer", 404

    if image is None or not image.filename:
        return "Missing image", 400

    original_filename = secure_filename(
        image.filename
    )

    suffix = Path(
        original_filename
    ).suffix.lower()

    if suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        return "Unsupported image format", 400

    image_filename = (
        f"{farmer_id}_"
        f"{uuid4().hex[:10]}"
        f"{suffix}"
    )

    image_path = (
        UPLOAD_DIR
        / image_filename
    )

    save_start = time.perf_counter()

    image.save(
        image_path
    )

    print(
        f"Image save: "
        f"{time.perf_counter() - save_start:.3f}s"
    )

    try:
        model_start = time.perf_counter()

        model = get_model()

        print(
            f"Model lookup/load: "
            f"{time.perf_counter() - model_start:.3f}s"
        )

        inference_start = time.perf_counter()

        result = model.classify(
            str(image_path)
        )

        print(
            f"Inference: "
            f"{time.perf_counter() - inference_start:.3f}s"
        )

    except Exception as exc:
        print(
            "Vision inference failed:",
            repr(exc),
        )

        return (
            "Could not analyze image.",
            500,
        )

    finally:
        delete_image(
            image_filename
        )

    print(
        "Vision preview:",
        {
            "farmer_id": farmer_id,
            "class": result.get("class"),
            "confidence": result.get(
                "confidence"
            ),
            "diagnosis": result.get(
                "diagnosis"
            ),
            "sure": result.get("sure"),
            "quality": result.get(
                "quality"
            ),
        },
    )

    farmer = farmers[farmer_id]

    render_start = time.perf_counter()

    response = render_template(
        "diagnosis_review.html",
        farmer_id=farmer_id,
        farmer=farmer,
        result=result,
    )

    print(
        f"Template render: "
        f"{time.perf_counter() - render_start:.3f}s"
    )

    print(
        f"TOTAL /diagnose: "
        f"{time.perf_counter() - total_start:.3f}s"
    )

    return response


# ---------------------------------------------------------
# Confirm diagnosis
# ---------------------------------------------------------

@vision_bp.post("/diagnose/confirm")
def confirm_diagnosis():
    total_start = time.perf_counter()

    farmer_id = request.form.get(
        "farmer_id",
        "",
    ).strip().upper()

    diagnosis = request.form.get(
        "diagnosis",
        "",
    ).strip()

    if not farmer_id or not diagnosis:
        return (
            "Missing diagnosis information",
            400,
        )

    farmers = load_farmers()

    if farmer_id not in farmers:
        return "Unknown farmer", 404

    if diagnosis == "unknown":
        return redirect("/")

    save_start = time.perf_counter()

    save_diagnosis(
        farmer_id=farmer_id,
        diagnosis=diagnosis,
    )

    print(
        f"Diagnosis SQLite save: "
        f"{time.perf_counter() - save_start:.3f}s"
    )

    print(
        "Confirmed diagnosis:",
        farmer_id,
        diagnosis,
    )

    print(
        f"TOTAL /diagnose/confirm: "
        f"{time.perf_counter() - total_start:.3f}s"
    )

    return redirect("/")


# ---------------------------------------------------------
# Cancel diagnosis
# ---------------------------------------------------------

@vision_bp.post("/diagnose/cancel")
def cancel_diagnosis():
    print("Diagnosis review cancelled")

    return redirect("/")


# ---------------------------------------------------------
# Persistence
# ---------------------------------------------------------

def save_diagnosis(
    farmer_id: str,
    diagnosis: str,
):
    row = {
        "farmer_id": farmer_id,
        "date": date.today().isoformat(),
        "diagnosis": diagnosis,
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO diagnoses (
                farmer_id,
                date,
                diagnosis
            )
            VALUES (?, ?, ?)
            """,
            (
                row["farmer_id"],
                row["date"],
                row["diagnosis"],
            ),
        )

    print(
        "Saved diagnosis to SQLite:",
        row,
    )


def delete_image(
    image_filename: str,
):
    if not image_filename:
        return

    start = time.perf_counter()

    filename = secure_filename(
        image_filename
    )

    image_path = (
        UPLOAD_DIR
        / filename
    )

    if image_path.exists():
        image_path.unlink()

    print(
        f"Image cleanup: "
        f"{time.perf_counter() - start:.3f}s"
    )