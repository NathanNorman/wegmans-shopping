# 🚀 Production Deployment Checklist

## ❌ Current Issue
**Error:** `supabaseKey is required`
**Cause:** Supabase environment variables not set in Render

---

## 🔧 Required: Add Environment Variables to Render

### Step 1: Go to Render Dashboard
1. Open: https://dashboard.render.com/
2. Find your `wegmans-shopping` service
3. Click on it
4. Go to **Environment** tab

### Step 2: Add These Environment Variables

```
SUPABASE_URL=https://pisakkjmyeobvcgxbmhk.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
```

**Where to get the keys:**
- Go to: https://supabase.com/dashboard/project/pisakkjmyeobvcgxbmhk/settings/api
- Copy the `anon` `public` key → paste as `SUPABASE_ANON_KEY`
- Copy the `service_role` `secret` key → paste as `SUPABASE_SERVICE_KEY`

### Step 3: Save and Redeploy
- Click **Save Changes** in Render
- Render will automatically redeploy
- Wait 2-3 minutes for deployment to complete

---

## 🌐 Configure Supabase for Production

### Step 1: Add Production URL to Supabase
1. Go to: https://supabase.com/dashboard/project/pisakkjmyeobvcgxbmhk/auth/url-configuration
2. Update **Site URL**:
   - Current: `http://localhost:8000`
   - Add: `https://your-app.onrender.com` (your actual Render URL)

3. Update **Redirect URLs**:
   - Current: `http://localhost:8000/**`
   - Add: `https://your-app.onrender.com/**`

**Note:** Keep both localhost (for development) and production URLs

---

## ✅ Verification Steps

After deploying:

1. **Check logs in Render:**
   ```
   ✓ Supabase client initialized
   ✅ Database connection successful
   ```

2. **Test in browser:**
   - Open your production URL
   - Check console - should see:
     ```
     ✓ Supabase client initialized
     ✓ User authenticated (if logged in)
     ```
   - Try signing up
   - Try adding items to cart
   - Verify everything works

3. **Test authentication:**
   - Sign up with new email
   - Check email arrives
   - Verify login works
   - Test password reset

---

## 🔒 Security Notes

**IMPORTANT:**
- ✅ `SUPABASE_ANON_KEY` is safe to expose (public key)
- ❌ `SUPABASE_SERVICE_KEY` must stay secret (never commit to git)
- ✅ Both are safe to add to Render environment variables
- ✅ Render keeps environment variables encrypted

---

## 📋 Complete Environment Variables List

Your Render environment should have:

```bash
# Database (already set)
DATABASE_URL=postgresql://...

# Supabase Auth (ADD THESE)
SUPABASE_URL=https://pisakkjmyeobvcgxbmhk.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...

# Optional
DEBUG=false
PORT=8000  # Render sets this automatically
```

---

## 🐛 If Still Not Working

**Check Render logs for errors:**
1. Go to Render dashboard → Your service → Logs
2. Look for errors during startup
3. Common issues:
   - Missing environment variable
   - Typo in variable name
   - Wrong key copied (anon vs service_role)

**Test locally first:**
```bash
# Set env vars
export SUPABASE_URL=https://pisakkjmyeobvcgxbmhk.supabase.co
export SUPABASE_ANON_KEY=your-key
export SUPABASE_SERVICE_KEY=your-key

# Run server
python3 -m uvicorn app:app --reload

# Should see: ✓ Supabase client initialized
```

---

## ⏱️ Estimated Time: 5 minutes

1. Get keys from Supabase (1 min)
2. Add to Render environment (2 min)
3. Wait for redeploy (2 min)
4. Test (1 min)

**That's it! Once you add the environment variables, the deployed version will work exactly like localhost.** 🎉
