#!/usr/bin/env python3
"""
Simple test script to analyze Rointe web authentication flow
Uses only standard library modules
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import re

def test_endpoint(url, method="GET", data=None):
    """Test a single endpoint"""
    try:
        if method == "POST" and data:
            data_bytes = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, method='POST')
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        else:
            req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode('utf-8')[:500]
    except urllib.error.HTTPError as e:
        return e.code, f"HTTP Error: {e.reason}"
    except Exception as e:
        return None, str(e)

def analyze_login_page():
    """Analyze the login page for API endpoints"""
    print("🔍 Analyzing login page...")
    
    try:
        with urllib.request.urlopen("https://rointenexa.com/", timeout=10) as response:
            content = response.read().decode('utf-8')
            
        print(f"Status: {response.status}")
        print(f"Content length: {len(content)}")
        
        # Look for JavaScript files that might contain API endpoints
        js_files = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', content)
        print(f"JavaScript files found: {js_files}")
        
        # Look for API endpoints in the content
        api_patterns = re.findall(r'["\']([^"\']*api[^"\']*)["\']', content, re.IGNORECASE)
        if api_patterns:
            print(f"Potential API endpoints: {api_patterns}")
        
        # Look for form action
        form_action = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if form_action:
            print(f"Form action: {form_action.group(1)}")
            
    except Exception as e:
        print(f"❌ Error analyzing login page: {e}")

def test_common_endpoints():
    """Test common authentication endpoints"""
    print("\n🔍 Testing common endpoints...")
    
    base_url = "https://rointenexa.com"
    endpoints = [
        "/api/auth/login",
        "/api/login", 
        "/auth/login",
        "/login",
        "/api/user/login",
        "/api/session/login",
        "/signin",
        "/auth"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        status, response = test_endpoint(url)
        print(f"{endpoint}: {status}")
        
        if status and status != 404:
            print(f"  ✅ Endpoint exists! Response: {response[:100]}...")

def main():
    print("🚀 Simple Rointe Web Authentication Analysis")
    print("=" * 50)
    
    analyze_login_page()
    test_common_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Analysis complete!")
    print("\nNext steps:")
    print("1. Look for working endpoints above")
    print("2. Check browser developer tools when logging in")
    print("3. Update integration to use web auth instead of Firebase")

if __name__ == "__main__":
    main()
