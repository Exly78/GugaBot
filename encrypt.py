"""
Run this once to encrypt your token.
It will generate:
  - token.enc       (push to GitHub)
  - dependencies.txt (push to GitHub)
  - config.txt      (keep local, add to .gitignore)
"""
from cryptography.fernet import Fernet

token = input("Paste your bot token: ").strip()
user_ids = input("Paste your Discord user ID(s) separated by commas: ").strip()

# Generate key
key = Fernet.generate_key()
f = Fernet(key)

# Encrypt token + user IDs together
payload = f"{token}\n{user_ids}".encode()
encrypted = f.encrypt(payload)

with open("token.enc", "wb") as file:
    file.write(encrypted)

with open("dependencies.txt", "wb") as file:
    file.write(key)

with open(".gitignore", "a") as file:
    file.write("\nconfig.txt\n")

print("\n✅ Done!")
print("  → Push token.enc and dependencies.txt to GitHub")
print("  → Never share dependencies.txt separately (but it's on GitHub here, so it's fine for your use case)")
