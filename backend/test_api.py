import requests
import pandas as pd
import random
import time
df = pd.read_csv("../dataset/creditcard.csv")
sample = df[df["Class"] == 0].drop("Class", axis=1).sample(1).iloc[0].to_dict()
sample["user_id"] = "user123"
sample["hour"] = random.randint(0, 23)
print("\nSending Transaction...")
print("Amount:", sample["Amount"])
print("Hour:", sample["hour"])
response = requests.post(
    "http://127.0.0.1:5000/predict",
    json=sample
)
print("\nStatus Code:", response.status_code)
try:
    result = response.json()
    print("\nResponse:")
    for key, value in result.items():
        print(f"{key}: {value}")
except ValueError as e:
    print(f"Raw Response: {response.text}\nError: {e}")
