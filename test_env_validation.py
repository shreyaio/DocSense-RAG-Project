#!/usr/bin/env python3
"""
Test script to verify that Qdrant initialization fails with clear error when credentials are missing.
"""
import os
import sys

# Clear env vars to simulate missing configuration
if "QDRANT_URL" in os.environ:
    del os.environ["QDRANT_URL"]
if "QDRANT_API_KEY" in os.environ:
    del os.environ["QDRANT_API_KEY"]

print("Testing Qdrant initialization without env vars...")
print("-" * 70)

try:
    from backend.config.settings import AppSettings
    print("✅ Step 1: AppSettings loaded successfully (graceful for local dev)")
    
    from backend.storage.qdrant_store import QdrantLocalStore
    print("✅ Step 2: QdrantLocalStore class imported successfully")
    
    # Now try to instantiate it - this should fail
    store = QdrantLocalStore()
    print("❌ FAIL: QdrantLocalStore instantiated successfully - should not happen!")
    sys.exit(1)
except RuntimeError as e:
    if "QDRANT_URL" in str(e) or "QDRANT_API_KEY" in str(e):
        print(f"✅ Step 3: Initialization failed with expected clear error")
        print(f"   Error: {e}")
        sys.exit(0)
    else:
        print(f"⚠️  UNEXPECTED RuntimeError: {e}")
        sys.exit(1)
except Exception as e:
    print(f"⚠️  UNEXPECTED: Got {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
