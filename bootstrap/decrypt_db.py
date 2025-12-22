import os
from dotenv import load_dotenv
from pathlib import Path
from cryptography.fernet import Fernet
load_dotenv()

ENC_DB_PATH = Path("secrets.db.enc")
DB_PATH = Path("secrets.db")

def main():
    # Safety checks
    if not ENC_DB_PATH.exists():
        raise FileNotFoundError("Encrypted DB not found")

    if DB_PATH.exists():
        raise RuntimeError("Plaintext secrets.db already exists")

    key = os.environ.get("DB_DECRYPTION_KEY")
    if not key:
        raise RuntimeError("DB_DECRYPTION_KEY is not set")

    fernet = Fernet(key.encode())

    encrypted_data = ENC_DB_PATH.read_bytes()
    decrypted_data = fernet.decrypt(encrypted_data)

    DB_PATH.write_bytes(decrypted_data)

    print("✅ secrets.db decrypted successfully")

if __name__ == "__main__":
    main()