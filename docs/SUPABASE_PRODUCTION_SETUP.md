# Supabase Production URL Configuration

## 🎯 What You're Looking For

You need to configure Supabase to accept authentication requests from your production URL.

---

## 📍 Step-by-Step Navigation

### Option 1: Authentication Settings (Most Likely Location)

1. **Go to your project:**
   - https://supabase.com/dashboard/project/pisakkjmyeobvcgxbmhk

2. **Click "Authentication" in left sidebar**

3. **Click "URL Configuration"** (should be a sub-menu item)
   - Or look for tabs at the top: Providers, Policies, Templates, **URL Configuration**

4. **You should see these fields:**
   - **Site URL** - The main URL of your app
   - **Redirect URLs** - Allowed URLs for auth redirects

5. **Add your production URL:**
   ```
   Site URL: https://wegmans-shopping.onrender.com

   Redirect URLs (one per line):
   http://localhost:8000/**
   https://wegmans-shopping.onrender.com/**
   ```

---

### Option 2: Project Settings (Alternative)

1. **Go to project:**
   - https://supabase.com/dashboard/project/pisakkjmyeobvcgxbmhk

2. **Click gear icon (⚙️) at bottom of left sidebar**
   - Or click "Settings" in left sidebar

3. **Click "Authentication"** in the settings menu

4. **Look for "Site URL" and "Redirect URLs" fields**

---

## 🔍 What These Fields Look Like

**Site URL:**
```
The base URL of your site
Example: https://my-app.com

[https://wegmans-shopping.onrender.com]  ← Enter your URL here
```

**Redirect URLs:**
```
Comma separated list of allowed URLs for redirects
Supports wildcards (*, **, ?). Use ** for every path/subdomain.

[http://localhost:8000/**
 https://wegmans-shopping.onrender.com/**]  ← One URL per line
```

---

## 🤔 Can't Find It?

Try these alternative locations:

### Check "API" Settings
1. Go to: Settings → API
2. Look for "Auth" or "Authentication" section
3. Might have URL configuration there

### Check Project Configuration
1. Settings → General
2. Look for "Auth Configuration" or "API Configuration"

### Check Authentication Providers
1. Authentication → Providers
2. Click on "Email" provider
3. Might have URL settings there

---

## 🆘 Still Can't Find It?

The setting might be called:
- "Site URL"
- "Redirect URLs"
- "OAuth Redirect URLs"
- "Allowed Redirect URLs"
- "Authentication URLs"
- "App URL"

**Search in Supabase docs:** https://supabase.com/docs/guides/auth/redirect-urls

Or just **skip this step for now** - it will work for development (localhost), and you can configure production URLs later when you find the setting!

---

## ✅ For Now: Just Add Render Environment Variables

The **critical step** is adding environment variables to Render:

1. Render Dashboard → Your Service → Environment
2. Add:
   ```
   SUPABASE_ANON_KEY=your-key
   SUPABASE_SERVICE_KEY=your-key
   ```

The Supabase URL configuration is a **nice-to-have** for password reset emails and OAuth redirects. The app will work without it for basic auth!

---

## 🎯 Priority Order

1. **MUST DO:** Add env vars to Render (app won't work without this)
2. **NICE TO HAVE:** Configure Supabase URLs (for password reset redirects)

Focus on #1 first, then we can figure out #2 later if needed!
