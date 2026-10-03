"""Tunable assumptions for FarmFlow. Change numbers here, not in code."""

# Advance rule: limit = ALPHA * (P10 forecast kg x first-payment price) - outstanding, capped.
# Conservative: uses the low-end forecast and ignores the second payment.
ALPHA = 0.30
CAP_RWF = 300_000      # raised with real prices: one bag of subsidised NPK is ~RWF 93,000
ROUND_TO_RWF = 1_000

# Confidence thresholds: below these the model says "not sure, ask a person".
TEXT_THRESHOLD = 0.55
VISION_THRESHOLD = 0.70

# Recommendations
MAX_ITEMS = 3

USSD_CODE = "*384*123#"   # placeholder; the Africa's Talking sandbox gives the real one
