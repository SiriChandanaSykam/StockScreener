import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

import google.generativeai as genai

def list_models():
    env_path = os.path.join(os.getcwd(), '.env')
    load_dotenv(env_path)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No API Key found.")
        return

    genai.configure(api_key=api_key)
    
    print("🔍 Listing available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- Name: {m.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_models()
