import requests
import json
import uuid
import sys

BASE_URL = "http://127.0.0.1:5000/api"
rand_hex = uuid.uuid4().hex[:6]
username = "test_user_v2_" + rand_hex
password = "password"
email = f"pravalikajunnu14+{rand_hex}@gmail.com"

try:
    print(f"Registering {username} with {email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "password": password,
        "email": email,
        "role": "admin"
    })
    print("Reg status:", reg_res.status_code, reg_res.text)

    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    try:
        data = login_res.json()
    except Exception as e:
        print("Failed to decode JSON from login res:", login_res.text)
        sys.exit(1)
        
    if "access_token" not in data:
        print("Login failed:", data)
        sys.exit(1)
        
    token = data["access_token"]
    print("Logged in successfully.")

    print("\nSending transaction check...")
    payload = {
        "amount": 95000, 
        "city": "Hyderabad", 
        "device_id": "sus_device_X", 
        "hour": 2, 
        "is_new_device": 1, 
        "transaction_frequency": 10, 
        "user_avg_amount": 500
    }

    headers = {"Authorization": f"Bearer {token}"}
    check_res = requests.post(f"{BASE_URL}/transactions/check", json=payload, headers=headers)

    print(f"Status Code: {check_res.status_code}")
    print(check_res.text)

except Exception as e:
    import traceback
    traceback.print_exc()
