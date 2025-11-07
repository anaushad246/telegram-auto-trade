import google.generativeai as genai
import config

try:
    print(f"--- Using API Key: {'*' * 10}{config.GEMINI_API_KEY[-4:]}")
    genai.configure(api_key=config.GEMINI_API_KEY)

    print("\n--- Available Models for 'generateContent' ---")
    
    # List all models
    for m in genai.list_models():
        # Check if the model supports the 'generateContent' method
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
            
    print("\nTest complete. You can now use one of the model names above.")

except Exception as e:
    print(f"\n--- ❌ AN ERROR OCCURRED ---")
    print(e)