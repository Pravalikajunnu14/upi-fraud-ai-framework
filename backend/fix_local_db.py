import sqlite3
conn = sqlite3.connect('c:/Users/prava/Desktop/upi_fraud_ai_framework/backend/database/upi_fraud.db')
conn.execute("UPDATE users SET email = 'junnupravalika59@gmail.com' WHERE username = 'admin'")
conn.commit()
conn.close()
print("Local database updated!")
