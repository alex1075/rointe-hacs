#!/usr/bin/env python3
"""
Detailed authentication test to debug Rointe login issues.
"""

import requests
import json

FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
SIGNIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

def test_detailed_authentication(email, password):
    """Test authentication with detailed debugging."""
    print(f"🧪 Testing authentication for: {email}")
    print(f"🔗 Using URL: {SIGNIN_URL}")
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        print("📡 Sending request...")
        response = requests.post(SIGNIN_URL, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"📊 Response Data: {json.dumps(data, indent=2)}")
        except:
            print(f"📊 Response Text: {response.text}")
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed!")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_alternative_endpoints(email, password):
    """Test alternative authentication endpoints."""
    print("\n🔍 Testing alternative authentication methods...")
    
    # Test with different Firebase project IDs or endpoints
    alternative_keys = [
        "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY",  # Current key
        # Add other possible keys if we find them
    ]
    
    for i, api_key in enumerate(alternative_keys):
        print(f"\n🧪 Testing with API key {i+1}: {api_key[:20]}...")
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ This API key works!")
                return True
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown")
                    print(f"   ❌ Error: {error_msg}")
                except:
                    print(f"   ❌ Error: {response.text[:100]}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return False

def main():
    print("🔐 Detailed Rointe Authentication Test")
    print("=" * 50)
    
    email = input("Enter your Rointe email: ").strip()
    password = input("Enter your Rointe password: ").strip()
    
    if not email or not password:
        print("❌ Email and password are required")
        return
    
    print(f"\n📧 Testing with email: {email}")
    print(f"🔑 Password length: {len(password)} characters")
    
    # Test main authentication
    success = test_detailed_authentication(email, password)
    
    if not success:
        # Test alternative endpoints
        success = test_alternative_endpoints(email, password)
    
    if success:
        print("\n✅ Authentication successful!")
        print("The credentials work with at least one endpoint.")
    else:
        print("\n❌ All authentication attempts failed!")
        print("\nPossible issues:")
        print("1. The website uses a different authentication method")
        print("2. Your account is configured for web-only access")
        print("3. The mobile app API endpoint has changed")
        print("4. There might be additional security measures")

if __name__ == "__main__":
    main()
