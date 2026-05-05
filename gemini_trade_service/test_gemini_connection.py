
import os
import sys
import logging
from google import genai
from google.genai import types
from service_config import service_config

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

def test_gemini_connection():
    print("--- Testing Gemini Connection ---")
    
    api_key = service_config.gemini_tier_1_2_api_key
    if not api_key:
        print("[ERROR] Error: API Key not found in service_config")
        return

    print(f"API Key found (length: {len(api_key)})")
    
    client = genai.Client(api_key=api_key)
    
    models_to_test = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    for model_name in models_to_test:
        print(f"\nTesting model: {model_name}")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, are you working?",
                config=types.GenerateContentConfig(
                    response_mime_type="text/plain",
                    temperature=0.1
                )
            )
            print(f"[OK] Success! Response: {response.text[:50]}...")
        except Exception as e:
            print(f"[ERROR] Failed: {e}")

if __name__ == "__main__":
    test_gemini_connection()
