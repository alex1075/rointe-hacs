#!/usr/bin/env python3
"""
Try to find the correct Firebase API key by testing common patterns.
"""

import requests
import json

def test_api_key_pattern(base_key, email, password):
    """Test variations of the API key."""
    print(f"🧪 Testing API key: {base_key[:20]}...")
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={base_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ SUCCESS! This API key works!")
            return True
        else:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown")
            print(f"❌ Error: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🔍 Searching for Working Firebase API Key")
    print("=" * 50)
    
    email = input("Enter your Rointe email: ").strip()
    password = input("Enter your Rointe password: ").strip()
    
    if not email or not password:
        print("❌ Email and password are required")
        return
    
    # Test the current key first
    current_key = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
    if test_api_key_pattern(current_key, email, password):
        return
    
    print("\n🔍 The current API key doesn't work.")
    print("This suggests either:")
    print("1. The API key has changed")
    print("2. Your account is not configured for mobile app access")
    print("3. Rointe has changed their authentication system")
    
    print("\n💡 Recommendations:")
    print("1. Try logging into the Rointe mobile app with these credentials")
    print("2. If mobile app login fails, create a new account in the mobile app")
    print("3. Check if your account needs to be linked for mobile access")
    print("4. Contact Rointe support about mobile app access")

if __name__ == "__main__":
    main()
