"""Create a local .env with random operator secrets without overwriting existing config."""
import base64
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[2]
target = root / ".env"
if target.exists():
    print(".env already exists; preserved. Check new settings in .env.example.")
else:
    content = (root / ".env.example").read_text()
    content = content.replace("CREDENTIAL_ENCRYPTION_KEY=", "CREDENTIAL_ENCRYPTION_KEY=" + base64.urlsafe_b64encode(os.urandom(32)).decode())
    content = content.replace("ADMIN_TOKEN=", "ADMIN_TOKEN=" + secrets.token_urlsafe(32))
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
    print("Created .env with local encryption and admin keys. Values are not printed.")
