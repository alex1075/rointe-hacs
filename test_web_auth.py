#!/usr/bin/env python3
"""
Test script to analyze Rointe web authentication flow
"""

import asyncio
import aiohttp
import json
from urllib.parse import urljoin

# Test credentials (replace with your actual credentials)
TEST_EMAIL = "your-email@example.com"
TEST_PASSWORD = "your-password"

class RointeWebAuth:
    def __init__(self):
        self.base_url = "https://rointenexa.com"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_login_page(self):
        """Test the login page to see what endpoints are available"""
        print("🔍 Testing login page...")
        
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                content = await response.text()
                print(f"Content length: {len(content)}")
                
                # Look for JavaScript that might reveal API endpoints
                if "api" in content.lower():
                    print("✅ Found 'api' in content")
                if "auth" in content.lower():
                    print("✅ Found 'auth' in content")
                if "login" in content.lower():
                    print("✅ Found 'login' in content")
                    
                # Look for common API patterns
                import re
                api_patterns = re.findall(r'["\']([^"\']*api[^"\']*)["\']', content, re.IGNORECASE)
                if api_patterns:
                    print(f"🔍 Potential API endpoints: {api_patterns}")
                    
        except Exception as e:
            print(f"❌ Error testing login page: {e}")
    
    async def test_common_auth_endpoints(self):
        """Test common authentication endpoints"""
        print("\n🔍 Testing common auth endpoints...")
        
        common_endpoints = [
            "/api/auth/login",
            "/api/login",
            "/auth/login",
            "/login",
            "/api/user/login",
            "/api/session/login"
        ]
        
        for endpoint in common_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    print(f"{endpoint}: {response.status}")
                    if response.status != 404:
                        print(f"  ✅ Endpoint exists!")
                        # Try POST to see if it accepts login data
                        try:
                            async with self.session.post(url, json={
                                "email": TEST_EMAIL,
                                "password": TEST_PASSWORD
                            }) as post_response:
                                print(f"  POST: {post_response.status}")
                        except:
                            pass
            except Exception as e:
                print(f"{endpoint}: Error - {e}")
    
    async def test_form_submission(self):
        """Test if the login form submits to a specific endpoint"""
        print("\n🔍 Testing form submission...")
        
        # Common form submission endpoints
        form_endpoints = [
            "/login",
            "/auth",
            "/signin",
            "/api/auth",
            "/api/login"
        ]
        
        for endpoint in form_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                # Try form data submission
                data = {
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "username": TEST_EMAIL,
                    "user": TEST_EMAIL
                }
                
                async with self.session.post(url, data=data) as response:
                    print(f"{endpoint} (form): {response.status}")
                    if response.status != 404:
                        print(f"  ✅ Form endpoint exists!")
                        print(f"  Response: {await response.text()[:200]}...")
                        
            except Exception as e:
                print(f"{endpoint} (form): Error - {e}")

async def main():
    print("🚀 Testing Rointe Web Authentication Flow")
    print("=" * 50)
    
    async with RointeWebAuth() as auth:
        await auth.test_login_page()
        await auth.test_common_auth_endpoints()
        await auth.test_form_submission()
    
    print("\n" + "=" * 50)
    print("✅ Web authentication analysis complete!")
    print("\nNext steps:")
    print("1. Check the output above for working endpoints")
    print("2. Update credentials in this script")
    print("3. Test actual authentication with working endpoints")

if __name__ == "__main__":
    asyncio.run(main())
