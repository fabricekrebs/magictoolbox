#!/usr/bin/env python3
"""Test script to create container in Azurite using REST API with proper authentication."""
import hmac
import hashlib
import base64
from datetime import datetime
import subprocess

account_name = "devstorageaccount1"
account_key = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
container = "test"

# Build request
date_str = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
version = "2021-08-06"

#String to sign
string_to_sign = (
    f"PUT\n\n\n0\n\n\n\n\n\n\n\n\n"
    f"x-ms-date:{date_str}\n"
    f"x-ms-version:{version}\n"
    f"/{account_name}/{container}\n"
    f"restype:container"
)

# Generate signature
signature = base64.b64encode(
    hmac.new(
        base64.b64decode(account_key),
        string_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
).decode('utf-8')

auth_header = f"SharedKey {account_name}:{signature}"

# Execute curl
cmd = [
    "curl", "-v", "-X", "PUT",
    f"http://127.0.0.1:10000/{account_name}/{container}?restype=container",
    "-H", f"x-ms-date: {date_str}",
    "-H", f"x-ms-version: {version}",
    "-H", f"Content-Length: 0",
    "-H", f"Authorization: {auth_header}"
]

print("Executing:")
print(" ".join(cmd))
print()

result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
print("Return code:", result.returncode)
