import sqlite3
for r in sqlite3.connect('backend/database/upi_fraud.db').execute('SELECT username, email FROM users'):
    print(r)
