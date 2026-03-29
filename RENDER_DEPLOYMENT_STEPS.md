# Render Deployment Guide

## Problem
You currently have a "Static Site" deployment, but you need a "Web Service" to run the Flask backend.

## Solution: Create Web Service on Render

### STEP 1: Delete Old Static Site (2 minutes)

1. Go to: https://dashboard.render.com
2. Click on **upi-fraud-dashboard** (in the left sidebar)
3. Scroll all the way DOWN to **Danger Zone** section
4. Click the RED button: **Delete Service**
5. Type the service name to confirm
6. Click **Delete Service**

**✅ Static Site is now deleted**

---

### STEP 2: Create NEW Web Service (5 minutes)

1. Go to: https://dashboard.render.com
2. Click: **+ New** button (top right)
3. Select: **Web Service**
4. When asked to "Connect a repository", click: **Connect GitHub**
5. Select: **Pravalikajunnu14/upi-fraud-ai-framework**
6. Click on that repository to continue

**On the next screen:**

| Field | Value |
|-------|-------|
| Name | `upi-fraud-dashboard` |
| Runtime | `Python 3.11` |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `cd backend && python app.py` |
| Environment | `production` |
| Plan | Free (or Starter) |

7. Click: **Create Web Service**

**⏳ It will take 2-5 minutes to build and deploy**

---

### STEP 3: Add Environment Variables (1 minute)

1. While it's deploying, go to: **Settings** (in the service page)
2. Click: **Environment** on the left
3. Add these variables:

```
FLASK_ENV = production
DEBUG = False
SECRET_KEY = my-secret-key-12345
JWT_SECRET_KEY = my-jwt-secret-12345
ALLOWED_ORIGINS = https://upi-fraud-dashboard.onrender.com
```

4. Click: **Save**

**⏳ Service will redeploy with new variables**

---

### STEP 4: Verify Deployment (2 minutes)

Once deployment completes:

1. Go to: https://upi-fraud-dashboard.onrender.com/api/health
   - Should show JSON with status and timestamp ✅

2. Go to: https://upi-fraud-dashboard.onrender.com/transactions.html
   - Should load transactions page ✅
   - Try logging in and submitting a transaction ✅

---

## Troubleshooting

**If you see "Cannot connect to server":**
- Check that deployment is complete (green "Live" button)
- Check Logs tab in Render dashboard for errors
- Wait 1-2 minutes and refresh the page

**If backend still not responding:**
- Check environment variables are set
- Check "Logs" tab for crash errors
- Common error: Missing packages → update requirements.txt

---

## Quick Summary

```
DELETE: Old Static Site
CREATE: New Web Service
CONFIGURE: Environment variables  
TEST: Health check + transactions page
```

**Total time: 10-15 minutes**

Once complete, your live site will be at:
✅ https://upi-fraud-dashboard.onrender.com
