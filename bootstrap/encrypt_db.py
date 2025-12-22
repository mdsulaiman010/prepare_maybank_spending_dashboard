from cryptography.fernet import Fernet

# Generate key
key = Fernet.generate_key()
fernet = Fernet(key)

# Read plaintext DB
with open("secrets.db", "rb") as f:
    plaintext = f.read()

# Perform encryption
encrypted = fernet.encrypt(plaintext)

# Write encrypted DB
with open("secrets.db.enc", "wb") as f:
    f.write(encrypted)

print("🔐 Encryption complete")
print("SAVE THIS KEY SECURELY:\n", key.decode())