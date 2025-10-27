# Simple Deployment Plan
## Wegmans Shopping App - Personal/Small Group Deployment

**Target Users:** 2-10 people (you + friends)
**Estimated Effort:** 8-12 hours
**Monthly Cost:** $5-20/month
**Deployment:** Single server, simple setup

---

## Goal

Get your working app on the internet with:
- ✅ HTTPS (secure)
- ✅ Simple password protection (optional)
- ✅ Reliable enough for personal use
- ✅ Easy to maintain
- ✅ Cheap to run

**NOT building:** Enterprise-scale infrastructure, multi-tenancy, load balancers, etc.

---

## Recommended Approach: Railway or Fly.io

### Option 1: Railway.app (Easiest, Recommended)
**Cost:** $5/month
**Effort:** 2-3 hours
**Pros:**
- Deploy from GitHub in minutes
- Automatic HTTPS
- Built-in PostgreSQL
- Zero DevOps required
- Great free tier to start

**Cons:**
- Slight vendor lock-in
- Limited control

### Option 2: Fly.io (More Control)
**Cost:** ~$10/month
**Effort:** 3-4 hours
**Pros:**
- Docker-based (portable)
- Multiple regions
- Good free tier
- More flexibility

**Cons:**
- More config needed
- Docker knowledge helpful

### Option 3: DigitalOcean Droplet (Most Control)
**Cost:** $6/month (basic droplet)
**Effort:** 6-8 hours
**Pros:**
- Full control
- SSH access
- Traditional VPS
- No surprises

**Cons:**
- You manage everything
- Manual HTTPS setup
- More maintenance

---

## Phase 1: Clean Up Current Code (2-3 hours)

### Step 1.1: Consolidate Entry Points (30 min)

**Delete redundant files:**
```bash
rm shop_interactive.py
rm create_shopping_list.py
mv interactive_list_builder.py server.py
```

**Create single `app.py`:**
```python
#!/usr/bin/env python3
"""
Wegmans Shopping App - Simple Production Server
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# API routes
@app.post("/api/search")
async def search_products(search_term: str):
    # Your existing search logic
    pass

@app.post("/api/cart")
async def save_cart(cart_data: dict):
    # Your existing cart save logic
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 1.2: Organize Files (30 min)

```bash
# Create directories
mkdir -p static/{css,js}
mkdir -p data

# Move HTML file
mv shop_ui_final.html static/index.html

# Move data files
mv cart.json selections.json search_results.json data/

# Update .gitignore
echo "data/*.json" >> .gitignore
echo ".env" >> .gitignore
```

**New structure:**
```
wegmans-shopping/
├── app.py                    # Main server
├── wegmans_scraper.py        # Keep as-is
├── requirements.txt          # Update deps
├── .gitignore
├── static/
│   └── index.html            # The UI
├── data/                     # Gitignored
│   ├── cart.json
│   └── search_results.json
└── README.md
```

### Step 1.3: Update Dependencies (15 min)

**requirements.txt:**
```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
playwright>=1.40.0
pydantic>=2.5.0
python-dotenv>=1.0.0
```

### Step 1.4: Add Configuration (15 min)

**Create `.env` file:**
```bash
# Server config
HOST=0.0.0.0
PORT=8000
STORE_LOCATION=Raleigh

# Optional: Simple password protection
SIMPLE_PASSWORD=your-secret-password-here
```

### Step 1.5: Test Locally (30 min)

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:8000` and verify everything works.

---

## Phase 2: Add Simple Security (1-2 hours)

### Option A: No Authentication (Simplest)
Just put it on the internet with a random URL like:
- `https://wegmans-shopping-abc123xyz.railway.app`
- Hard to guess = good enough for 2 friends

### Option B: Simple Password (Basic Auth)
Add HTTP Basic Auth to FastAPI:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("SIMPLE_PASSWORD", "changeme")
    is_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    if not is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Protect all routes
@app.get("/", dependencies=[Depends(verify_password)])
async def serve_frontend():
    return FileResponse("static/index.html")
```

Browser will prompt for password. Username doesn't matter.

### Option C: Simple Login Page (Better UX)
- Add a login page
- Store session in cookie
- 1-2 hours more work

**Recommendation for 2-10 users:** Option A (obscure URL) or Option B (basic auth).

---

## Phase 3A: Deploy to Railway (Easiest - 1 hour)

### Step 1: Create `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python app.py",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Step 2: Deploy
1. Go to railway.app, sign up (free)
2. "New Project" → "Deploy from GitHub repo"
3. Select your repo
4. Railway auto-detects Python, installs deps, runs app
5. Click "Generate Domain" → Get HTTPS URL instantly

### Step 3: Add Environment Variables
In Railway dashboard:
- `STORE_LOCATION` = `Raleigh`
- `SIMPLE_PASSWORD` = `your-password` (optional)

### Step 4: Install Playwright in Railway
Add to your `requirements.txt`:
```txt
playwright>=1.40.0
```

Add `Procfile`:
```
web: playwright install chromium && python app.py
```

**Done!** You have `https://your-app.railway.app`

**Cost:** Free for hobby use, $5/month for more

---

## Phase 3B: Deploy to Fly.io (More Control - 2-3 hours)

### Step 1: Install Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
fly auth signup  # or fly auth login
```

### Step 2: Create `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
```

### Step 3: Initialize Fly App
```bash
fly launch
# Follow prompts:
# - App name: wegmans-shopping
# - Region: Choose closest to you
# - PostgreSQL: No (we're using JSON files for now)
# - Redis: No
```

This creates `fly.toml`:
```toml
app = "wegmans-shopping"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"
  STORE_LOCATION = "Raleigh"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
```

### Step 4: Deploy
```bash
fly deploy
fly open  # Opens your app in browser
```

### Step 5: Add Secrets (Optional)
```bash
fly secrets set SIMPLE_PASSWORD=your-secret-password
```

**Done!** You have `https://wegmans-shopping.fly.dev`

**Cost:** Free tier covers 2-3 VMs, then ~$10/month

---

## Phase 3C: Deploy to DigitalOcean (Most Control - 4-6 hours)

### Step 1: Create Droplet ($6/month)
1. Go to digitalocean.com
2. Create Droplet:
   - Ubuntu 22.04 LTS
   - Basic plan: $6/month (1 GB RAM)
   - Choose datacenter near you

### Step 2: Initial Server Setup (30 min)
```bash
# SSH into server
ssh root@your-server-ip

# Create non-root user
adduser wegmans
usermod -aG sudo wegmans

# Switch to new user
su - wegmans
```

### Step 3: Install Dependencies (30 min)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3-pip python3.11-venv -y

# Install Playwright dependencies
sudo apt install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2
```

### Step 4: Deploy App (1 hour)
```bash
# Clone your repo
git clone https://github.com/yourusername/wegmans-shopping.git
cd wegmans-shopping

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt
playwright install chromium

# Create .env file
nano .env
# Add: STORE_LOCATION=Raleigh

# Test run
python app.py
# Visit http://your-server-ip:8000
```

### Step 5: Setup Systemd Service (30 min)
```bash
sudo nano /etc/systemd/system/wegmans.service
```

Add:
```ini
[Unit]
Description=Wegmans Shopping App
After=network.target

[Service]
User=wegmans
WorkingDirectory=/home/wegmans/wegmans-shopping
Environment="PATH=/home/wegmans/wegmans-shopping/venv/bin"
ExecStart=/home/wegmans/wegmans-shopping/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable wegmans
sudo systemctl start wegmans
sudo systemctl status wegmans
```

### Step 6: Setup NGINX + HTTPS (1 hour)
```bash
# Install NGINX
sudo apt install nginx certbot python3-certbot-nginx -y

# Configure NGINX
sudo nano /etc/nginx/sites-available/wegmans
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use IP for now

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/wegmans /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Get Free SSL with Let's Encrypt (15 min)

**If you have a domain:**
```bash
sudo certbot --nginx -d your-domain.com
```

**If you don't have a domain:**
- Buy a cheap domain ($10/year) from Namecheap/Porkbun
- Point A record to your server IP
- Run certbot command above

**Or use IP address** (no HTTPS):
- Just use `http://your-server-ip`
- Not secure, but fine for personal use with friends

**Done!** You have `https://your-domain.com`

---

## What About Data Persistence?

### Current: JSON Files (Fine for 2-10 users)

Your current approach works:
```
data/
├── cart.json          # Each user's cart
├── selections.json    # User selections
└── search_cache.json  # Search results cache
```

**Limitations:**
- Not concurrent-safe (2 users editing cart = race condition)
- Manual backups needed
- Lost if server dies

**Solutions:**

### Option 1: Keep JSON, Add Backups (Simplest)
```bash
# Daily backup cron job
0 2 * * * tar -czf ~/backups/data-$(date +\%Y\%m\%d).tar.gz ~/wegmans-shopping/data/
```

Good for: 1-3 users who don't use it simultaneously

### Option 2: SQLite Database (Better)
- Single file database
- ACID compliance
- No extra server needed
- Handles concurrent access

**Add to requirements.txt:**
```txt
sqlalchemy>=2.0.0
```

**Create simple schema:**
```python
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ShoppingCart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    items = Column(JSON)

engine = create_engine('sqlite:///data/wegmans.db')
Base.metadata.create_all(engine)
```

Good for: 2-10 users

### Option 3: PostgreSQL (Overkill, but robust)
- Railway/Fly.io offer managed PostgreSQL
- $5-10/month extra
- Better for 10+ users

Good for: If you plan to grow beyond 10 users

**Recommendation:** Start with JSON + backups, upgrade to SQLite if needed.

---

## Deployment Comparison

| Feature | Railway | Fly.io | DigitalOcean |
|---------|---------|--------|--------------|
| **Ease** | ⭐⭐⭐⭐⭐ Easiest | ⭐⭐⭐⭐ Easy | ⭐⭐ Manual |
| **Cost** | $5/mo | $10/mo | $6/mo |
| **Setup Time** | 1 hour | 2-3 hours | 4-6 hours |
| **Auto HTTPS** | ✅ Yes | ✅ Yes | ❌ Manual |
| **Auto Deploy** | ✅ Yes (Git push) | ✅ Yes | ❌ Manual |
| **Control** | ⭐⭐ Limited | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Full |
| **Maintenance** | ⭐⭐⭐⭐⭐ None | ⭐⭐⭐⭐ Minimal | ⭐⭐ You handle |
| **Scalability** | ⭐⭐⭐ OK | ⭐⭐⭐⭐ Good | ⭐⭐⭐ DIY |

**Recommendation:**
- **Starting out:** Railway (easiest)
- **More control:** Fly.io (good balance)
- **Budget + experience:** DigitalOcean (cheapest, but more work)

---

## Step-by-Step: Railway Deployment (Recommended)

### Total Time: ~2 hours

#### Step 1: Cleanup Local Code (30 min)
```bash
# Consolidate files
rm shop_interactive.py create_shopping_list.py
mkdir static data
mv shop_ui_final.html static/index.html
mv *.json data/

# Create app.py with FastAPI
# (Use code from Phase 1)
```

#### Step 2: Test Locally (15 min)
```bash
pip install fastapi uvicorn
python app.py
# Visit http://localhost:8000
```

#### Step 3: Push to GitHub (15 min)
```bash
git add .
git commit -m "Prepare for deployment"
git push
```

#### Step 4: Deploy to Railway (30 min)
1. Go to railway.app
2. Sign in with GitHub
3. New Project → Deploy from GitHub
4. Select your repo
5. Wait for build (~2-3 minutes)
6. Click "Generate Domain"
7. Visit your URL!

#### Step 5: Configure (15 min)
In Railway dashboard:
- Add environment variable: `STORE_LOCATION=Raleigh`
- Restart app

#### Step 6: Share with Friends (1 min)
Send them the URL: `https://your-app.railway.app`

**Done!** 🎉

---

## Security Considerations (For Small Group)

### Must Have:
1. ✅ **HTTPS** - All platforms provide this
2. ✅ **Obscure URL** - Hard to guess = security through obscurity
3. ✅ **Keep dependencies updated** - `pip install -U -r requirements.txt`

### Nice to Have:
4. ⚠️ **Basic Auth** - Simple password protection (add if needed)
5. ⚠️ **Rate limiting** - Prevents abuse (optional for small group)
6. ⚠️ **CORS** - Only allow your domain (optional)

### Don't Need:
- ❌ OAuth/JWT - Overkill for 2-10 friends
- ❌ DDoS protection - Cloudflare free tier if needed
- ❌ Load balancing - Single server handles 100+ concurrent users
- ❌ Database replication - SQLite backup is fine

---

## Monitoring (Optional but Recommended)

### Free Options:

#### 1. UptimeRobot (uptime monitoring)
- Free tier: Check every 5 minutes
- Email alert if site goes down
- Setup: 5 minutes

#### 2. Railway/Fly.io Built-in Logs
- View logs in dashboard
- Search for errors
- Good enough for small apps

#### 3. Simple Health Check Endpoint
Add to your FastAPI app:
```python
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
```

Point UptimeRobot at `https://your-app.com/health`

---

## Backup Strategy

### For JSON Files:
```bash
# Manual backup (run monthly)
scp your-server:/path/to/data/*.json ~/backups/

# Or use Railway CLI
railway volume download
```

### For SQLite:
```bash
# Automatic nightly backup (if using DigitalOcean)
0 2 * * * sqlite3 /path/to/wegmans.db ".backup '/path/to/backups/wegmans-$(date +\%Y\%m\%d).db'"
```

### For PostgreSQL (if using):
Railway/Fly.io have automatic backups included.

---

## Cost Breakdown

### Railway (Recommended)
- **Hobby plan:** $5/month
- **Includes:** 500 execution hours, $5 credit
- **Good for:** 2-20 users

### Fly.io
- **Free tier:** 3 VMs (enough for small app)
- **Paid:** ~$10/month if you exceed free tier
- **Good for:** 5-50 users

### DigitalOcean
- **Droplet:** $6/month (1GB RAM)
- **Domain:** $10/year (optional)
- **Total:** ~$6-7/month
- **Good for:** Any size, but more maintenance

### Domain (Optional)
- **Namecheap/Porkbun:** $8-15/year
- **Not required:** Railway/Fly.io give you free subdomain

**Total: $5-10/month** (or $0 if using free tiers)

---

## Timeline

### Phase 1: Code Cleanup (2-3 hours)
- ✅ Consolidate entry points
- ✅ Organize file structure
- ✅ Add configuration
- ✅ Test locally

### Phase 2: Security (30 min - 1 hour)
- ✅ Add basic auth (optional)
- ✅ Environment variables
- ✅ Update .gitignore

### Phase 3: Deploy (1-4 hours depending on platform)
- Railway: 1 hour
- Fly.io: 2-3 hours
- DigitalOcean: 4-6 hours

### Phase 4: Test & Share (1 hour)
- ✅ Test all features
- ✅ Add monitoring
- ✅ Share with friends

**Total: 5-10 hours** (depending on platform choice)

---

## Next Steps

1. **Choose deployment platform:** Railway (easiest) or Fly.io (more control)
2. **Phase 1: Clean up code** (we can do this now)
3. **Phase 2: Add basic security** (optional, 30 min)
4. **Phase 3: Deploy** (1-2 hours)
5. **Test and share** (30 min)

**Want me to start with Phase 1 (code cleanup)?** We can knock that out in 30 minutes and you'll be deployment-ready.
