"""
patch_emails.py — one-time script to add emails to existing seeded users.
"""
import sqlite3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from config import Config

conn = sqlite3.connect(Config.DB_PATH)

# Add emails to seeded accounts that never had one
conn.execute(
    "UPDATE users SET email = 'admin@upishield.com' WHERE username = 'admin' AND (email IS NULL OR email = '')"
)
conn.execute(
    "UPDATE users SET email = 'user@upishield.com' WHERE username = 'user' AND (email IS NULL OR email = '')"
)
conn.commit()

print("\n=== Current Users ===")
for row in conn.execute("SELECT id, username, email, role FROM users"):
    uid, uname, uemail, urole = row[0], row[1], row[2] or "(none)", row[3]
    print(f"  [{uid}] {uname:10s} | {uemail:35s} | {urole}")

conn.close()
print("\nDone!")
