#!/usr/bin/env python
"""Quick test to verify provider imports work correctly."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.analyst.providers import get_provider, LMStudioProvider, GCloudProvider


def test_providers():
    """Test provider abstraction layer."""
    print("=" * 50)
    print("Provider Configuration Test")
    print("=" * 50)

    print(f"\nConfiguration loaded:")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  GCloud Project: {config.gcloud_project}")
    print(f"  GCloud Model: {config.gcloud_model}")
    print(f"  GCloud Region: {config.gcloud_region}")
    print(f"  Service Account Key Path: {config.gcloud_service_account_key_path or 'Not set'}")

    # Test provider factory
    print(f"\nTesting provider factory...")

    # Test LM Studio provider (should always work - no external dependencies)
    print("\n1. Testing LM Studio provider...")
    try:
        lm_studio = get_provider('lm_studio')
        print(f"   SUCCESS: provider_name={lm_studio.provider_name}, model_name={lm_studio.model_name}")
    except Exception as e:
        print(f"   FAILED: {e}")

    # Test GCloud provider (requires service account key)
    print("\n2. Testing GCloud provider...")
    try:
        gcloud = get_provider('gcloud')
        print(f"   SUCCESS: provider_name={gcloud.provider_name}, model_name={gcloud.model_name}")
    except Exception as e:
        print(f"   FAILED (expected without service account key): {type(e).__name__}")

    # Test PostClassifier with explicit provider
    print("\n3. Testing PostClassifier with LM Studio provider (explicit)...")
    try:
        from app.analyst.classifier import PostClassifier
        classifier = PostClassifier(provider_name='lm_studio')
        print(f"   SUCCESS: provider_name={classifier._provider_name}, model_name={classifier.model_name}")
    except Exception as e:
        print(f"   FAILED: {e}")

    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)


if __name__ == "__main__":
    test_providers()
