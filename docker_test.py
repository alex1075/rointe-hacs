#!/usr/bin/env python3
"""
Quick Docker setup for testing Rointe integration.
"""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    print("🐳 Setting up Docker-based Home Assistant for Rointe testing")
    print("=" * 60)
    
    # Check if Docker is available
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not installed or not available.")
            print("Please install Docker Desktop from: https://www.docker.com/products/docker-desktop")
            return 1
        print(f"✅ Docker found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Docker command not found. Please install Docker Desktop.")
        return 1
    
    # Create HA configuration directory
    config_dir = Path.home() / ".homeassistant"
    config_dir.mkdir(exist_ok=True)
    
    custom_components_dir = config_dir / "custom_components"
    custom_components_dir.mkdir(exist_ok=True)
    
    # Copy integration to custom_components
    print("\n📁 Copying Rointe integration to Home Assistant...")
    rointe_source = Path("custom_components/rointe")
    rointe_dest = custom_components_dir / "rointe"
    
    if not rointe_source.exists():
        print("❌ Rointe integration not found. Make sure you're in the correct directory.")
        return 1
    
    if rointe_dest.exists():
        shutil.rmtree(rointe_dest)
    
    shutil.copytree(rointe_source, rointe_dest)
    print("✅ Integration copied successfully!")
    
    # Create docker-compose.yml
    print("\n📝 Creating docker-compose.yml...")
    docker_compose = """version: '3.8'
services:
  homeassistant:
    container_name: rointe-test-ha
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - ${PWD}/.homeassistant:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    network_mode: host
    environment:
      - TZ=UTC
    ports:
      - "8123:8123"
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    print("✅ docker-compose.yml created!")
    
    # Create basic configuration.yaml
    config_yaml = custom_components_dir.parent / "configuration.yaml"
    if not config_yaml.exists():
        print("\n📝 Creating basic configuration.yaml...")
        basic_config = """# Basic Home Assistant configuration for testing
default_config:

# Enable debug logging for Rointe integration
logger:
  logs:
    custom_components.rointe: debug
    homeassistant.components.climate: debug

# Basic recorder config
recorder:
  purge_keep_days: 1
  commit_interval: 1
"""
        with open(config_yaml, "w") as f:
            f.write(basic_config)
        print("✅ Basic configuration.yaml created!")
    
    print("\n" + "=" * 60)
    print("🎉 Docker setup complete!")
    print("\nTo start Home Assistant:")
    print("  docker-compose up -d")
    print("\nTo access Home Assistant:")
    print("  http://localhost:8123")
    print("\nTo stop Home Assistant:")
    print("  docker-compose down")
    print("\nTo view logs:")
    print("  docker-compose logs -f homeassistant")
    print("\nTo restart Home Assistant:")
    print("  docker-compose restart")
    
    print("\n📋 Testing Checklist:")
    print("1. Start Home Assistant: docker-compose up -d")
    print("2. Wait for startup (check logs)")
    print("3. Open http://localhost:8123")
    print("4. Complete initial HA setup")
    print("5. Go to Settings → Devices & Services → Add Integration")
    print("6. Search for 'Rointe' and configure")
    print("7. Verify your devices appear as climate entities")
    
    print("\n🔍 Debug Tips:")
    print("- Check logs: docker-compose logs -f homeassistant")
    print("- Enable debug logging in configuration.yaml")
    print("- Check custom_components/rointe directory exists")
    print("- Verify Rointe credentials are correct")
    
    return 0

if __name__ == "__main__":
    exit(main())
