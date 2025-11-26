import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

# Load your login details
load_dotenv()
LOGIN = int(os.getenv("MT5_LOGIN", 0))
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")

# --- PASTE YOUR PATH HERE IF THE DEFAULT FAILS ---
# Example: r"C:\Program Files\OctaFX MetaTrader 5\terminal64.exe"
CUSTOM_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" 

print(f"🔍 Testing connection to Account: {LOGIN} on Server: {SERVER}")

# Attempt 1: Auto-detect
print("\n--- Attempt 1: Auto-detection ---")
if mt5.initialize():
    print("✅ Success! Connected via Auto-detection.")
    print(mt5.account_info())
    mt5.shutdown()
else:
    print(f"❌ Failed: {mt5.last_error()}")

# Attempt 2: Specific Path
print(f"\n--- Attempt 2: Using Path: {CUSTOM_PATH} ---")
if mt5.initialize(path=CUSTOM_PATH):
    print("✅ Success! MT5 Launched.")
    
    # Now try to login
    if mt5.login(LOGIN, password=PASSWORD, server=SERVER):
        print("✅ Login Successful!")
        print(f"   Balance: {mt5.account_info().balance}")
    else:
        print(f"❌ Login Failed: {mt5.last_error()}")
    
    mt5.shutdown()
else:
    print(f"❌ Launch Failed: {mt5.last_error()}")