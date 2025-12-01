#!/usr/bin/env python3
"""
Generate a secure API key for CYT API Server
Run this script and add the output to your shell profile or startup script:
    export CYT_API_KEY="generated_key_here"
"""
import secrets

def generate_api_key():
    """Generate a cryptographically secure API key"""
    key = secrets.token_urlsafe(32)
    return key

if __name__ == "__main__":
    api_key = generate_api_key()
    print("=" * 70)
    print("CYT API KEY GENERATED")
    print("=" * 70)
    print(f"\nYour secure API key: {api_key}\n")
    print("Add this to your environment:")
    print(f"    export CYT_API_KEY=\"{api_key}\"")
    print("\nOr add to ~/.bashrc or ~/.zshrc for persistence:")
    print(f"    echo 'export CYT_API_KEY=\"{api_key}\"' >> ~/.bashrc")
    print("\nThen reload your shell or run:")
    print("    source ~/.bashrc")
    print("\nTest the API server:")
    print(f"    curl -H \"X-API-Key: {api_key}\" http://localhost:8080/status")
    print("=" * 70)
