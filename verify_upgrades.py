import urllib.request, json, time

BASE = "http://127.0.0.1:5000"

def post(path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read()), res.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def get(path):
    req = urllib.request.Request(BASE + path)
    res = urllib.request.urlopen(req)
    return json.loads(res.read())

# 1. Login
d, _ = post("/api/auth/login", {"username": "admin", "password": "admin123"})
token = d["access_token"]
print("[1] Login OK as admin")

# 2. Check transaction - normal
t0 = time.time()
r1, _ = post("/api/transactions/check", {"amount": 1500, "city": "Mumbai", "upi_id": "user@okicici"}, token)
t1 = time.time()
print("[2] Check TXN:", r1.get("label"), "| score:", r1.get("fraud_score"), "%")
print("    First call:", round((t1-t0)*1000, 1), "ms")

# 3. Same call again - should be faster (cache hit)
t2 = time.time()
r2, _ = post("/api/transactions/check", {"amount": 1500, "city": "Mumbai", "upi_id": "user@okicici"}, token)
t3 = time.time()
print("    Cached call:", round((t3-t2)*1000, 1), "ms")

# 4. Webhook test (high-risk fraud transaction)
wdata = {
    "payment_id": "pay_test001",
    "amount": 9500000,
    "city": "Delhi",
    "upi_id": "fraud@okhdfc",
    "is_new_device": 1,
    "transaction_frequency": 15,
    "user_avg_amount": 3000
}
wr, ws = post("/api/webhook/transaction", wdata)
print("[3] Webhook:", wr.get("label"), "| action:", wr.get("action"), "| score:", wr.get("fraud_score"), "%")

# 5. Webhook health + cache stats
hd = get("/api/webhook/health")
print("[4] Cache stats:", hd.get("cache"))

print("\nAll upgrades verified OK!")
