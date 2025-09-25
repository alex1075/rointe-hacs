#!/usr/bin/env python3
"""
Simple test script that doesn't require Home Assistant installation.
Tests basic Python functionality and file structure.
"""

import os
import sys
from pathlib import Path

def test_file_structure():
    """Test that all required files exist."""
    print("🧪 Testing file structure...")
    
    required_files = [
        "custom_components/rointe/__init__.py",
        "custom_components/rointe/manifest.json",
        "custom_components/rointe/auth.py",
        "custom_components/rointe/api.py",
        "custom_components/rointe/ws.py",
        "custom_components/rointe/climate.py",
        "custom_components/rointe/config_flow.py",
        "custom_components/rointe/const.py",
        "custom_components/rointe/strings.json",
        "custom_components/rointe/translations/en.json",
        "hacs.json",
        "README.md",
        "LICENSE",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present!")
        return True

def test_manifest():
    """Test manifest.json structure."""
    print("\n🧪 Testing manifest.json...")
    
    try:
        import json
        with open("custom_components/rointe/manifest.json", "r") as f:
            manifest = json.load(f)
        
        required_fields = ["domain", "name", "version", "requirements", "config_flow"]
        missing_fields = [field for field in required_fields if field not in manifest]
        
        if missing_fields:
            print(f"❌ Missing manifest fields: {missing_fields}")
            return False
        
        # Check specific values
        assert manifest["domain"] == "rointe"
        assert manifest["name"] == "Rointe Nexa"
        assert manifest["config_flow"] is True
        assert "aiohttp" in manifest["requirements"]
        
        print("✅ Manifest.json is valid!")
        return True
    except Exception as e:
        print(f"❌ Manifest test failed: {e}")
        return False

def test_hacs_json():
    """Test hacs.json structure."""
    print("\n🧪 Testing hacs.json...")
    
    try:
        import json
        with open("hacs.json", "r") as f:
            hacs = json.load(f)
        
        required_fields = ["name", "domain", "homeassistant"]
        missing_fields = [field for field in required_fields if field not in hacs]
        
        if missing_fields:
            print(f"❌ Missing HACS fields: {missing_fields}")
            return False
        
        assert hacs["domain"] == "rointe"
        assert hacs["name"] == "Rointe Nexa"
        
        print("✅ hacs.json is valid!")
        return True
    except Exception as e:
        print(f"❌ HACS test failed: {e}")
        return False

def test_strings_json():
    """Test strings.json structure."""
    print("\n🧪 Testing strings.json...")
    
    try:
        import json
        with open("custom_components/rointe/strings.json", "r") as f:
            strings = json.load(f)
        
        # Check basic structure
        assert "config" in strings
        assert "step" in strings["config"]
        assert "error" in strings["config"]
        
        # Check user step exists
        assert "user" in strings["config"]["step"]
        user_step = strings["config"]["step"]["user"]
        assert "title" in user_step
        assert "description" in user_step
        assert "data" in user_step
        
        print("✅ strings.json is valid!")
        return True
    except Exception as e:
        print(f"❌ strings.json test failed: {e}")
        return False

def test_translations():
    """Test translations structure."""
    print("\n🧪 Testing translations...")
    
    try:
        import json
        with open("custom_components/rointe/translations/en.json", "r") as f:
            translations = json.load(f)
        
        # Check basic structure
        assert "config" in translations
        
        print("✅ translations/en.json is valid!")
        return True
    except Exception as e:
        print(f"❌ translations test failed: {e}")
        return False

def test_python_syntax():
    """Test Python syntax of all Python files."""
    print("\n🧪 Testing Python syntax...")
    
    python_files = [
        "custom_components/rointe/__init__.py",
        "custom_components/rointe/auth.py",
        "custom_components/rointe/api.py",
        "custom_components/rointe/ws.py",
        "custom_components/rointe/climate.py",
        "custom_components/rointe/config_flow.py",
        "custom_components/rointe/const.py",
    ]
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()
            compile(content, file_path, "exec")
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
        except Exception as e:
            syntax_errors.append(f"{file_path}: {e}")
    
    if syntax_errors:
        print("❌ Python syntax errors found:")
        for error in syntax_errors:
            print(f"  {error}")
        return False
    else:
        print("✅ All Python files have valid syntax!")
        return True

def test_imports_basic():
    """Test basic imports without Home Assistant."""
    print("\n🧪 Testing basic imports...")
    
    try:
        # Test standard library imports
        import json
        import logging
        import asyncio
        from datetime import datetime, timedelta
        from typing import Optional, Dict, Any
        import re
        
        print("✅ All standard library imports successful!")
        
        # Test optional imports
        try:
            import aiohttp
            print("✅ aiohttp available")
        except ImportError:
            print("⚠️  aiohttp not installed (will be installed with Home Assistant)")
        
        try:
            import voluptuous as vol
            print("✅ voluptuous available")
        except ImportError:
            print("⚠️  voluptuous not installed (will be installed with Home Assistant)")
        
        return True
    except ImportError as e:
        print(f"❌ Basic import failed: {e}")
        return False

def test_constants():
    """Test constants file."""
    print("\n🧪 Testing constants...")
    
    try:
        with open("custom_components/rointe/const.py", "r") as f:
            content = f.read()
        
        # Check that required constants are defined
        required_constants = ["DOMAIN", "PLATFORMS"]
        for constant in required_constants:
            if f"{constant} =" not in content:
                print(f"❌ Missing constant: {constant}")
                return False
        
        print("✅ Constants file is valid!")
        return True
    except Exception as e:
        print(f"❌ Constants test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Rointe Integration Simple Tests")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_manifest,
        test_hacs_json,
        test_strings_json,
        test_translations,
        test_python_syntax,
        test_imports_basic,
        test_constants,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        print("\n✅ Integration structure is correct!")
        print("\nNext steps for full testing:")
        print("1. Install Home Assistant (Docker or Python)")
        print("2. Run: python docker_test.py (for Docker setup)")
        print("3. Or run: python test_setup.py (for full setup)")
        print("4. Test with real Rointe devices")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
