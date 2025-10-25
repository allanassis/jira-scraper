#!/usr/bin/env python3
"""Setup script for development environment."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return None


def main():
    """Set up the development environment."""
    print("🚀 Setting up Jira Scraper development environment")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install package in development mode
    run_command("pip install -e .", "Installing package")
    
    # Install development dependencies
    run_command("pip install pytest pytest-asyncio pytest-mock black isort mypy", 
                "Installing development dependencies")
    
    # Run tests to verify installation
    result = run_command("python -m pytest tests/ -v", "Running tests")
    if result is None:
        print("⚠️  Tests failed, but setup continues")
    
    # Create output directory
    Path("output").mkdir(exist_ok=True)
    print("✅ Created output directory")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("  1. Run demo: python demo.py")
    print("  2. Run tests: make test")
    print("  3. Start scraping: make scrape-small")
    print("  4. See all commands: make help")


if __name__ == "__main__":
    main()
