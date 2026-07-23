import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import numpy as np
from api.models import KnownFace, FaceImage
from api.services.embedding_cache import EmbeddingCache
from api.services.recognition_service import RecognitionService
from api.utils.preprocessing import EmbeddingNormalizer
from api.config.thresholds import Thresholds

print("=" * 60)
print("FACE RECOGNITION DIAGNOSTIC (with tightened thresholds)")
print("=" * 60)

print(f"\nThresholds:")
print(f"  SIMILARITY_THRESHOLD: {Thresholds.SIMILARITY_THRESHOLD}")
print(f"  CONFIDENCE_THRESHOLD: {Thresholds.CONFIDENCE_THRESHOLD}")
print(f"  LIVE_MATCH_MARGIN:    {Thresholds.LIVE_MATCH_MARGIN}")

EmbeddingCache.refresh()
cache = EmbeddingCache.get_all()

# 1. Test registered faces against cache (self-recognition)
print("\n--- 1. REGISTERED FACE SELF-TEST ---")
for entry in cache:
    avg = np.array(entry["averaged"], dtype=np.float32)
    match, distance, confidence = RecognitionService.recognize_face_cached(avg)
    match_name = match["name"] if match else None
    status = "PASS" if match_name == entry["name"] else "FAIL"
    print(f"  '{entry['name']}': match='{match_name}', dist={distance:.4f}, conf={confidence:.1f}% -> {status}")

# 2. Test individual images
print("\n--- 2. INDIVIDUAL IMAGE TEST ---")
for entry in cache:
    for idx, n_vec in enumerate(entry["normalized"]):
        test_emb = np.array(n_vec, dtype=np.float32)
        match, distance, confidence = RecognitionService.recognize_face_cached(test_emb)
        match_name = match["name"] if match else None
        status = "PASS" if match_name == entry["name"] else "FAIL"
        print(f"  '{entry['name']}' img[{idx}]: match='{match_name}', dist={distance:.4f}, conf={confidence:.1f}% -> {status}")

# 3. Simulate unknown faces by adding noise to known embeddings
print("\n--- 3. UNKNOWN FACE SIMULATION (noisy embeddings) ---")
np.random.seed(42)
for entry in cache:
    avg = np.array(entry["averaged"], dtype=np.float32)
    for noise_level in [0.3, 0.5, 0.7, 0.9]:
        noise = np.random.randn(128).astype(np.float32)
        noise = noise / np.linalg.norm(noise) * noise_level
        noisy_emb = avg + noise
        noisy_emb = EmbeddingNormalizer.normalize_l2(noisy_emb)
        match, distance, confidence = RecognitionService.recognize_face_cached(noisy_emb)
        match_name = match["name"] if match else "Unknown"
        status = "PASS" if match is None else "FAIL (false positive!)"
        print(f"  noise={noise_level:.1f} near '{entry['name']}': match='{match_name}', dist={distance:.4f}, conf={confidence:.1f}% -> {status}")

# 4. Generate completely random embeddings (simulating random unknown faces)
print("\n--- 4. RANDOM UNKNOWN FACE TEST ---")
for i in range(5):
    random_emb = np.random.randn(128).astype(np.float32)
    random_emb = EmbeddingNormalizer.normalize_l2(random_emb)
    match, distance, confidence = RecognitionService.recognize_face_cached(random_emb)
    match_name = match["name"] if match else "Unknown"
    status = "PASS" if match is None else "FAIL (false positive!)"
    print(f"  Random {i+1}: match='{match_name}', dist={distance:.4f}, conf={confidence:.1f}% -> {status}")

# 5. Cross-pair distances for reference
print("\n--- 5. ALL CROSS-PERSON DISTANCES ---")
for i in range(len(cache)):
    for j in range(i + 1, len(cache)):
        avg_i = np.array(cache[i]["averaged"], dtype=np.float32)
        avg_j = np.array(cache[j]["averaged"], dtype=np.float32)
        d = float(1.0 - np.dot(avg_i, avg_j))
        bar = " <-- BELOW THRESHOLD!" if d < Thresholds.SIMILARITY_THRESHOLD else ""
        print(f"  '{cache[i]['name']}' vs '{cache[j]['name']}': {d:.4f}{bar}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
