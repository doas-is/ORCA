from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

# Get API key
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

# Initialize client
client = genai.Client(api_key=api_key)

print("🔍 Fetching available Gemini models...\n")
print("=" * 80)

try:
    # List all models
    models = client.models.list()
    
    print(f"Found {len(models)} models:\n")
    
    for model in models:
        print(f"📦 {model.name}")
        if hasattr(model, 'display_name'):
            print(f"   Display: {model.display_name}")
        if hasattr(model, 'description'):
            print(f"   Description: {model.description[:100]}...")
        if hasattr(model, 'supported_generation_methods'):
            print(f"   Methods: {model.supported_generation_methods}")
        print()
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTrying alternative approach...")
    
    # Try specific models that should exist
    test_models = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro',
        'gemini-1.5-pro-latest',
        'gemini-pro',
        'gemini-flash',
    ]
    
    print("\n🧪 Testing specific models:\n")
    for model_name in test_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, respond with 'OK'"
            )
            print(f"✅ {model_name} - WORKS")
        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg:
                print(f"❌ {model_name} - NOT FOUND")
            elif '429' in error_msg:
                print(f"⚠️  {model_name} - RATE LIMITED (but exists)")
            else:
                print(f"❓ {model_name} - {error_msg[:50]}")

print("\n" + "=" * 80)