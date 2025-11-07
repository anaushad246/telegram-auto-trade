import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv()
print("--- DEBUGGING .ENV ---")

# --- Telegram ---
API_ID = os.getenv("API_ID", 0)
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")
print(f"Loaded API_ID: {'*' * 5 if API_ID else 'MISSING'}")
print(f"Loaded API_HASH: {'*' * 5 if API_HASH else 'MISSING'}")
print(f"Loaded PHONE: {'*' * 5 if PHONE else 'MISSING'}")

# (This is new) Reads the comma-separated list of group names
GROUP_NAMES_STR = os.getenv("GROUP_NAMES", "")
GROUP_NAMES = [group.strip() for group in GROUP_NAMES_STR.split(',') if group.strip()]
print(f"Loaded GROUP_NAMES: {GROUP_NAMES_STR if GROUP_NAMES_STR else 'MISSING'}")

# --- MetaTrader 5 ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
print(f"Loaded MT5_LOGIN: {'*' * 5 if MT5_LOGIN else 'MISSING'}")
print(f"Loaded MT5_PASSWORD: {'*' * 5 if MT5_PASSWORD else 'MISSING'}")
print(f"Loaded MT5_SERVER: {MT5_SERVER if MT5_SERVER else 'MISSING'}")

# --- AI & Trade Logic ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
print(f"Loaded GEMINI_API_KEY: {'*' * 5 if GEMINI_API_KEY else 'MISSING'}")

FIXED_LOT_SIZE = float(os.getenv("FIXED_LOT_SIZE", 0.01))
print(f"Loaded FIXED_LOT_SIZE: {FIXED_LOT_SIZE}")
print("------------------------")

# --- Validation ---
# We convert API_ID and MT5_LOGIN to int *before* checking them
if not all([API_ID, API_HASH, PHONE, GROUP_NAMES, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, GEMINI_API_KEY]):
    print("\n❌ VALIDATION FAILED. At least one variable is 'MISSING' or empty.")
    raise ValueError("One or more required environment variables are missing. Check your .env file (API_ID, API_HASH, PHONE, GROUP_NAMES, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, GEMINI_API_KEY).")
else:
    print("\n✅ VALIDATION PASSED. All variables loaded.")