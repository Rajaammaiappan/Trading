# Short Option Pro — Deployment Guide

## Files in this folder
```
shortoptionpro/
├── app.py              ← Flask server (your backend)
├── templates/
│   └── index.html      ← Web app UI
├── requirements.txt    ← Python packages needed
├── Procfile            ← Tells Render how to start the app
└── .gitignore          ← Files to not upload to GitHub
```

---

## STEP-BY-STEP: Deploy to Render (Free)

### PHASE 1 — Set up GitHub (one time)

**Step 1:** Go to https://github.com and create a free account if you don't have one.

**Step 2:** Click the "+" button (top right) → "New repository"
- Name it: `short-option-pro`
- Keep it Private (important — this is your trading app)
- Click "Create repository"

**Step 3:** Install Git on your computer
- Windows: https://git-scm.com/download/win  → download and install
- Mac: open Terminal and type: `git --version` (it will auto-install)

**Step 4:** Open Terminal (Mac) or Command Prompt (Windows)
Type these commands one by one:

```bash
cd Desktop
mkdir short-option-pro
cd short-option-pro
```

**Step 5:** Copy all the files from this folder into `short-option-pro` on your Desktop.
(app.py, requirements.txt, Procfile, .gitignore, and the templates folder)

**Step 6:** In Terminal, inside the `short-option-pro` folder, run:

```bash
git init
git add .
git commit -m "first upload"
git branch -M main
git remote add origin https://github.com/Rajaammaiappan/short-option-pro.git
git push -u origin main
```
Replace YOUR_GITHUB_USERNAME with your actual GitHub username.

When it asks for username/password — use your GitHub username and a Personal Access Token (not your password). To get one: GitHub → Settings → Developer Settings → Personal Access Tokens → Generate new token → check "repo" → copy it.

---

### PHASE 2 — Deploy on Render (Free hosting)

**Step 7:** Go to https://render.com → Sign up with your GitHub account.

**Step 8:** Click "New +" → "Web Service"

**Step 9:** Click "Connect a repository" → select `short-option-pro`

**Step 10:** Fill in the settings:
- **Name:** short-option-pro (or anything you like)
- **Region:** Singapore (closest to India)
- **Branch:** main
- **Runtime:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Instance Type:** Free

**Step 11:** Click "Create Web Service"

Render will now build and deploy your app. This takes 2–3 minutes.

**Step 12:** Once deployed, Render gives you a URL like:
`https://short-option-pro.onrender.com`

Open that URL in any browser — your app is live!

---

### PHASE 3 — Share with your team

Send the URL to your trading group. They can open it on:
- Any browser (Chrome, Safari, Firefox)
- Mobile phone
- Tablet
- Any computer

No installation needed for them.

---

## Important Notes

**Free tier limitations on Render:**
- The app "sleeps" after 15 minutes of no activity
- First load after sleep takes ~30 seconds to wake up
- To avoid this, upgrade to "Starter" plan ($7/month)

**Database:**
- The free Render plan stores the database on the server
- If Render restarts the server, the database resets
- For permanent data, add a free PostgreSQL database on Render (ask for help when ready)

**Updating the app:**
Every time you change your code, just run:
```bash
git add .
git commit -m "update"
git push
```
Render will automatically redeploy in 1–2 minutes.

---

## Troubleshooting

**App not loading:** Wait 30 seconds — it may be waking from sleep.

**"Application error":** Check Render logs (Render dashboard → your service → Logs tab).

**Market data shows "Simulated":** NSE blocks some servers. This is normal — your calculations and all features still work perfectly.
