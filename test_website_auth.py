#!/usr/bin/env python3
"""
Test to understand how Rointe website authentication works.
"""

import requests
import json

def test_rointe_website_auth():
    """Test different possible Rointe website authentication endpoints."""
    
    print("🌐 Testing Rointe Website Authentication Methods")
    print("=" * 60)
    
    # Possible Rointe website endpoints
    endpoints = [
        "https://rointenexa.com/api/auth/login",
        "https://rointenexa.com/api/login", 
        "https://rointenexa.com/login",
        "https://rointenexa.com/auth/login",
        "https://rointenexa.com/user/login",
        "https://rointenexa.com/api/user/login",
    ]
    
    email = input("Enter your Rointe email: ").strip()
    password = input("Enter your Rointe password: ").strip()
    
    if not email or not password:
        print("❌ Email and password are required")
        return
    
    print(f"\n📧 Testing with email: {email}")
    
    for endpoint in endpoints:
        print(f"\n🧪 Testing endpoint: {endpoint}")
        
        # Try different payload formats
        payloads = [
            {"email": email, "password": password},
            {"username": email, "password": password},
            {"user": email, "pass": password},
            {"login": email, "password": password},
            {"email": email, "pwd": password},
        ]
        
        for i, payload in enumerate(payloads):
            try:
                print(f"   📝 Trying payload format {i+1}: {list(payload.keys())}")
                
                response = requests.post(endpoint, json=payload, timeout=10)
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code != 404:
                    try:
                        data = response.json()
                        print(f"   📋 Response: {json.dumps(data, indent=2)[:200]}...")
                    except:
                        print(f"   📋 Response: {response.text[:200]}...")
                
                if response.status_code == 200:
                    print("   ✅ SUCCESS! This endpoint works!")
                    return endpoint, payload
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ Network error: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print("\n❌ No working website endpoints found")
    print("\nThis suggests the website might use:")
    print("1. A different authentication method (OAuth, SAML, etc.)")
    print("2. JavaScript-based authentication")
    print("3. A different API endpoint not tested here")
    print("4. Session-based authentication with cookies")

if __name__ == "__main__":
    test_rointe_website_auth()
