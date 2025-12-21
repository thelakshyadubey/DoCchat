# Railway Deployment Guide for Dochat

## Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app)
- Your Google Drive API credentials

---

## Step 1: Prepare Your Code for Git

1. **Initialize Git Repository:**

   ```powershell
   git init
   git add .
   git commit -m "Initial commit - prepare for Railway deployment"
   ```

2. **Create GitHub Repository:**

   - Go to https://github.com/new
   - Create a new repository (name: `dochat` or similar)
   - DON'T initialize with README, .gitignore, or license

3. **Push to GitHub:**
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

---

## Step 2: Prepare Google Drive Credentials

1. **Encode your token.json file to Base64:**

   Open PowerShell and run:

   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes("token.json")
   $base64 = [System.Convert]::ToBase64String($bytes)
   $base64 | Out-File -FilePath google_creds_base64.txt
   Write-Host "Base64 encoded credentials saved to google_creds_base64.txt"
   ```

2. **Keep this file safe** - you'll need to paste its contents into Railway

---

## Step 3: Deploy on Railway

### 3.1 Create New Project

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select your `dochat` repository

### 3.2 Add PostgreSQL Database

1. In your Railway project dashboard, click "+ New"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway will automatically:
   - Create the database
   - Set the `DATABASE_URL` environment variable

### 3.3 Configure Environment Variables

1. Click on your app service (not the database)
2. Go to "Variables" tab
3. Click "+ New Variable" and add each of these:

   ```
   SECRET_KEY=your-secret-key-here-use-a-long-random-string
   GROQ_API_KEY=your-groq-api-key
   GROQ_MODEL=llama3-70b-8192
   FLASK_ENV=production
   RAILWAY_ENVIRONMENT=true
   GOOGLE_CREDENTIALS_BASE64=<paste-contents-from-google_creds_base64.txt>
   ```

   **Important Notes:**

   - For `SECRET_KEY`, generate a secure random string (50+ characters)
   - Copy your GROQ API key from https://console.groq.com/keys
   - For `GOOGLE_CREDENTIALS_BASE64`, open `google_creds_base64.txt` and copy ALL the text
   - `DATABASE_URL` is automatically set by Railway when you add PostgreSQL

### 3.4 Deploy

1. Railway will automatically deploy after you push to GitHub
2. First deployment takes 5-10 minutes
3. Watch the "Deployments" tab for progress

---

## Step 4: Set Up Persistent Storage (Critical!)

Your app uses local file storage for uploads and embeddings. Railway's filesystem is ephemeral (resets on restart).

### Option A: Add Railway Volumes (Recommended)

1. In your service, click "Settings"
2. Scroll to "Volumes"
3. Click "+ Add Volume"
4. Create two volumes:

   - **Volume 1:**

     - Mount Path: `/app/uploads`
     - Name: `dochat-uploads`

   - **Volume 2:**
     - Mount Path: `/app/embeddings`
     - Name: `dochat-embeddings`

5. Click "Save" and redeploy

### Option B: Migrate to Cloud Storage (Better for Production)

For production, consider migrating to:

- **Google Cloud Storage** - Integrates well with your Drive setup
- **AWS S3** - Industry standard
- **Azure Blob Storage** - Another option

This requires code changes to upload files to cloud storage instead of local disk.

---

## Step 5: Verify Deployment

1. **Get Your App URL:**

   - In Railway dashboard, go to "Settings"
   - Under "Domains", click "Generate Domain"
   - Your app will be at: `https://your-app-name.up.railway.app`

2. **Test Your App:**

   - Visit the URL
   - Try registering a new account
   - Upload a PDF
   - Test the chat functionality

3. **Check Logs:**
   - Click "Deployments" tab
   - Click on the latest deployment
   - View "View Logs" to see any errors

---

## Step 6: Database Initialization

The database tables should be created automatically on first run. If you see database errors:

1. **Connect to PostgreSQL via Railway:**

   - In Railway, click on your PostgreSQL service
   - Go to "Connect" tab
   - Copy the `DATABASE_URL`

2. **Run psql locally** (if you have it installed):

   ```powershell
   $env:DATABASE_URL="postgresql://..."
   psql $env:DATABASE_URL
   ```

3. **Create tables manually** (if needed):
   ```sql
   -- Run these commands in psql
   \c dochat
   -- Tables should auto-create from database.py
   ```

---

## Step 7: Enable Auto-Deploy

Railway auto-deploys when you push to GitHub:

1. Make changes locally
2. Commit: `git add . && git commit -m "Your changes"`
3. Push: `git push`
4. Railway automatically rebuilds and deploys

---

## Troubleshooting

### App Crashes on Startup

**Check logs:**

```
Railway Dashboard → Deployments → View Logs
```

**Common issues:**

- Missing environment variables
- Database connection failed
- Google Drive credentials invalid

### Database Connection Errors

1. Verify `DATABASE_URL` is set in Variables
2. Check PostgreSQL service is running
3. Restart both services

### Google Drive Upload Fails

1. Verify `GOOGLE_CREDENTIALS_BASE64` is set correctly
2. Check the base64 string has no line breaks
3. Ensure your token.json has proper refresh token

### File Upload Fails

1. Verify volumes are mounted at `/app/uploads` and `/app/embeddings`
2. Check service has write permissions
3. Look for "Permission denied" errors in logs

### Memory/Timeout Issues

If your app is slow or times out:

1. Upgrade your Railway plan (free tier has limits)
2. Reduce `--workers` in Procfile (change to 1)
3. Optimize model loading (use smaller sentence-transformers model)

---

## Cost Estimation

**Railway Free Tier:**

- $5 free credit per month
- Good for testing
- May need upgrade for production

**Paid Plans:**

- Hobby: $5/month base + usage
- Pro: $20/month base + usage
- Usage charges: ~$0.000231/GB-hour for compute

**Tip:** Monitor usage in Railway dashboard to avoid surprises.

---

## Security Checklist

✅ **Before going live:**

- [ ] Strong `SECRET_KEY` (50+ random characters)
- [ ] Google credentials stored as base64 environment variable
- [ ] Database password is auto-generated by Railway
- [ ] No sensitive files in Git (check .gitignore)
- [ ] HTTPS is enabled (automatic on Railway domains)
- [ ] Set up custom domain with SSL (optional)

---

## Production Best Practices

1. **Set up monitoring:**

   - Use Railway's built-in logs
   - Consider adding Sentry for error tracking

2. **Regular backups:**

   - Railway Pro includes automated PostgreSQL backups
   - Export volumes regularly

3. **Update dependencies:**

   ```powershell
   pip list --outdated
   pip install --upgrade package-name
   ```

4. **Monitor costs:**
   - Check Railway dashboard weekly
   - Set up billing alerts

---

## Next Steps

1. **Custom Domain (Optional):**

   - Settings → Domains → Add Custom Domain
   - Point your DNS to Railway

2. **CI/CD Pipeline:**

   - GitHub Actions for testing before deploy
   - Automated database migrations

3. **Scale Up:**
   - Increase workers in Procfile
   - Upgrade Railway plan
   - Add Redis for caching

---

## Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Your Logs:** Railway Dashboard → Deployments → View Logs

---

## Quick Commands Reference

```powershell
# View local requirements
pip list

# Test locally before deploying
$env:FLASK_ENV="development"
python app.py

# Check git status
git status

# Push changes to deploy
git add .
git commit -m "Update message"
git push

# View Railway logs (install CLI first)
railway logs

# Connect to Railway PostgreSQL
railway connect PostgreSQL
```

---

## Important Files Created

- ✅ `.gitignore` - Prevents sensitive files from being committed
- ✅ `Procfile` - Tells Railway how to run your app
- ✅ `requirements.txt` - Updated with gunicorn
- ✅ `runtime.txt` - Specifies Python version
- ✅ `RAILWAY_DEPLOYMENT.md` - This guide

---

## Deployment Checklist

**Before deploying:**

- [ ] Git repository created and pushed to GitHub
- [ ] Google credentials encoded to base64
- [ ] All environment variables ready
- [ ] Tested app locally

**During deployment:**

- [ ] Railway project created
- [ ] PostgreSQL database added
- [ ] Environment variables configured
- [ ] Persistent volumes added
- [ ] Domain generated

**After deployment:**

- [ ] App URL works
- [ ] Can register and login
- [ ] File upload works
- [ ] Chat functionality works
- [ ] Check logs for errors

---

**You're all set! Your app should now be live on Railway. 🚀**
