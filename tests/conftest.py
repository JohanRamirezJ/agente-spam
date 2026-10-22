import os

# A developer's real .env must never change test behaviour (tokens, thresholds, limits).
os.environ["AGENTE_NO_DOTENV"] = "1"
