#!/usr/bin/env python3
"""
Test different Firebase projects for Rointe authentication.
"""

import requests
import json

# Common Firebase API keys that might be used by Rointe
FIREBASE_KEYS = [
    "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY",  # Current key
    # Add other possible keys if we find them
]

def test_firebase_key(api_key, email, password):
    """Test authentication with a specific Firebase API key."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
    except Exception as e:
        return None, str(e)

def main():
    print("🔐 Testing Different Firebase Projects")
    print("=" * 50)
    
    email = input("Enter your Rointe email: ").strip()
    password = input("Enter your Rointe password: ").strip()
    
    if not email or not password:
        print("❌ Email and password are required")
        return
    
    print(f"\n📧 Testing with email: {email}")
    
    for i, api_key in enumerate(FIREBASE_KEYS):
        print(f"\n🧪 Testing Firebase project {i+1}: {api_key[:20]}...")
        
        status_code, response = test_firebase_key(api_key, email, password)
        
        if status_code == 200:
            print("✅ SUCCESS! This API key works!")
            print(f"📋 Response: {json.dumps(response, indent=2)}")
            return
        elif status_code == 400:
            if isinstance(response, dict):
                error_msg = response.get("error", {}).get("message", "Unknown error")
                print(f"❌ Error: {error_msg}")
            else:
                print(f"❌ Error: {response}")
        else:
            print(f"❌ Status {status_code}: {response}")
    
    print("\n❌ No working Firebase projects found")
    print("\nPossible solutions:")
    print("1. The Firebase API key might have changed")
    print("2. Rointe might be using a different authentication method")
    print("3. Your account might not be configured for mobile app access")
    print("4. There might be additional security measures")

if __name__ == "__main__":
    main()
