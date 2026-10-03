"""The fixed list of diagnoses FarmFlow can talk about.

Every model output maps onto one of these keys, so every message the system can
send is known in advance (the brief's "fixed list of answers").
"""

DIAGNOSES = {
    "leaf_rust":      "leaf rust",
    "brown_eye_spot": "brown eye spot",
    "leaf_miner":     "leaf miner",
    "berry_disease":  "berry disease",
    "pests":          "insect pests",
    "nutrient":       "nutrient shortage",
    "drought":        "drought stress",
    "old_trees":      "old trees",
    "healthy":        "no disease seen",
    "unknown":        "not sure",
}

# Text-model labels are what farmers DESCRIBE; they map to a likely diagnosis
# that the washing station then confirms with a photo where possible.
TEXT_LABEL_TO_DIAGNOSIS = {
    "yellow_orange_spots": "leaf_rust",
    "brown_spots":         "brown_eye_spot",
    "leaf_tunnels":        "leaf_miner",
    "berries_black_drop":  "berry_disease",
    "insects":             "pests",
    "leaves_pale":         "nutrient",
    "wilting_dry":         "drought",
    "old_low_yield":       "old_trees",
    "other":               "unknown",
}

# Vision classes depend on the BRACOL folder names. Martin: map each folder here.
VISION_CLASS_TO_DIAGNOSIS = {
    "healthy":   "healthy",
    "rust":      "leaf_rust",
    "leaf_rust": "leaf_rust",
    "miner":     "leaf_miner",
    "leaf_miner": "leaf_miner",
    "cercospora": "brown_eye_spot",
    "brown_leaf_spot": "brown_eye_spot",
    "phoma":     "unknown",
}

# Diagnoses that need a photo or a person before any treatment is suggested
NEEDS_CONFIRMATION = {"leaf_rust", "brown_eye_spot", "leaf_miner", "berry_disease", "pests"}
