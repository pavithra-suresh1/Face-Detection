import io
import json
import uuid
import urllib.request
from PIL import Image

BASE = "http://localhost:8000/api"

login_data = json.dumps({"username": "demo", "password": "testpass123"}).encode()
req = urllib.request.Request(f"{BASE}/auth/login/", data=login_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["access"]
print(f"Login OK")

img = Image.new("RGB", (100, 100), color="blue")
buf = io.BytesIO()
img.save(buf, format="JPEG")
img_data = buf.getvalue()

boundary = uuid.uuid4().hex
body_parts = []
body_parts.append(f"--{boundary}\r\n".encode())
body_parts.append(b'Content-Disposition: form-data; name="name"\r\n')
body_parts.append(b"\r\n")
body_parts.append(b"New User Test\r\n")
body_parts.append(f"--{boundary}\r\n".encode())
body_parts.append(b'Content-Disposition: form-data; name="reference_image"; filename="test.jpg"\r\n')
body_parts.append(b"Content-Type: image/jpeg\r\n")
body_parts.append(b"\r\n")
body_parts.append(img_data)
body_parts.append(b"\r\n")
body_parts.append(f"--{boundary}--\r\n".encode())
body = b"".join(body_parts)

req = urllib.request.Request(f"{BASE}/known-faces/create/", data=body)
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
req.add_header("Authorization", f"Bearer {token}")

try:
    resp = urllib.request.urlopen(req)
    print("SUCCESS:", resp.status)
    print(resp.read().decode())
except urllib.request.HTTPError as e:
    print(f"ERROR {e.code}: {e.read().decode()}")
