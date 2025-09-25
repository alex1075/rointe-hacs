#!/usr/bin/env python3
"""
Test script for the new dual authentication system

Tests both REST API and Firebase authentication flows.
"""

import asyncio
import logging
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from rointe.auth import RointeAuth, RointeRestAuthError, RointeFirebaseAuthError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Test credentials (replace with your actual credentials)
TEST_EMAIL = "your-email@example.com"
TEST_PASSWORD = "your-password"

async def test_dual_authentication():
    """Test the dual authentication system"""
    print("🚀 Testing Rointe Dual Authentication System")
    print("=" * 60)
    
    # Create auth instance
    auth = RointeAuth(TEST_EMAIL, TEST_PASSWORD)
    
    try:
        async with auth:
            print(f"📧 Testing with email: {TEST_EMAIL}")
            print()
            
            # Test 1: REST API Authentication
            print("🔐 Test 1: REST API Authentication")
            print("-" * 40)
            try:
                await auth.async_login_rest()
                print("✅ REST API authentication successful")
                
                # Get REST token
                rest_token = await auth.async_rest_token()
                print(f"🔑 REST token: {rest_token[:20]}..." if rest_token else "❌ No REST token")
                
                # Get user ID
                user_id = auth.get_user_id()
                print(f"👤 User ID: {user_id}")
                
                print(f"✅ REST token valid: {auth.is_rest_token_valid()}")
                
            except RointeRestAuthError as e:
                print(f"❌ REST API authentication failed: {e}")
                return False
            except Exception as e:
                print(f"❌ Unexpected error in REST auth: {e}")
                return False
            
            print()
            
            # Test 2: Firebase Authentication
            print("🔥 Test 2: Firebase Authentication")
            print("-" * 40)
            try:
                await auth.async_login_firebase()
                print("✅ Firebase authentication successful")
                
                # Get Firebase token
                firebase_token = await auth.async_firebase_token()
                print(f"🔑 Firebase token: {firebase_token[:20]}..." if firebase_token else "❌ No Firebase token")
                
                print(f"✅ Firebase token valid: {auth.is_firebase_token_valid()}")
                
            except RointeFirebaseAuthError as e:
                print(f"❌ Firebase authentication failed: {e}")
                print("⚠️  WebSocket functionality will be limited")
            except Exception as e:
                print(f"❌ Unexpected error in Firebase auth: {e}")
                print("⚠️  WebSocket functionality will be limited")
            
            print()
            
            # Test 3: Token Refresh
            print("🔄 Test 3: Token Refresh")
            print("-" * 40)
            try:
                # Test REST token refresh
                rest_token_2 = await auth.async_rest_token()
                print(f"🔄 REST token refreshed: {rest_token_2[:20]}..." if rest_token_2 else "❌ REST token refresh failed")
                
                # Test Firebase token refresh
                if auth.is_firebase_token_valid():
                    firebase_token_2 = await auth.async_firebase_token()
                    print(f"🔄 Firebase token refreshed: {firebase_token_2[:20]}..." if firebase_token_2 else "❌ Firebase token refresh failed")
                else:
                    print("⚠️  Firebase token not available for refresh test")
                
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
            
            print()
            
            # Test 4: Credential Validation
            print("✅ Test 4: Credential Validation")
            print("-" * 40)
            try:
                is_valid = await auth.async_validate_credentials()
                print(f"✅ Credentials valid: {is_valid}")
            except Exception as e:
                print(f"❌ Credential validation failed: {e}")
            
            print()
            print("=" * 60)
            print("🎉 Dual Authentication Test Completed!")
            print()
            print("📋 Summary:")
            print(f"  • REST API Auth: {'✅ Working' if auth.is_rest_token_valid() else '❌ Failed'}")
            print(f"  • Firebase Auth: {'✅ Working' if auth.is_firebase_token_valid() else '❌ Failed'}")
            print(f"  • User ID: {auth.get_user_id() or '❌ Not available'}")
            
            return True
            
    except Exception as e:
        print(f"❌ Fatal error during authentication test: {e}")
        return False

async def main():
    """Main test function"""
    if TEST_EMAIL == "your-email@example.com" or TEST_PASSWORD == "your-password":
        print("❌ Please update TEST_EMAIL and TEST_PASSWORD in this script with your actual credentials")
        print("   Edit the script and replace the placeholder values")
        return
    
    success = await test_dual_authentication()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Commit and push these changes to your repository")
        print("2. Test the integration in Home Assistant")
        print("3. Check that both REST API and WebSocket functionality work")
    else:
        print("\n❌ Authentication test failed. Please check your credentials and network connection.")

if __name__ == "__main__":
    asyncio.run(main())
