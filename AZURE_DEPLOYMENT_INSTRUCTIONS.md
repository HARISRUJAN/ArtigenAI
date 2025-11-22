# Azure App Service Deployment Instructions

## Overview

This document explains how to deploy the ArtigenAI application to Azure App Service using the configured GitHub Actions workflow.

## Prerequisites

✅ **Already Configured:**
- Azure App Service resource (`artigen`)
- GitHub Actions workflow (`version-0.1_artigen.yml`)
- Azure service principal credentials (stored as GitHub secrets)

## Deployment Process

### How the Deployment Works

The GitHub Actions workflow automatically:

1. **Builds the Frontend**
   - Sets up Node.js 18
   - Installs frontend dependencies
   - Builds the React app
   - Copies the built static files to `backend/static/`

2. **Prepares the Backend**
   - Sets up Python 3.11
   - Installs Python dependencies from `backend/requirements.txt`
   - Creates deployment artifact with all necessary files

3. **Deploys to Azure**
   - Uploads the application to Azure App Service
   - Runs `startup.sh` to start the application
   - Application serves both API and frontend from a single FastAPI app

### Triggering a Deployment

The workflow triggers on pushes to the `Version-0.1` branch:

```bash
# Option 1: Push directly to Version-0.1 branch
git checkout Version-0.1
git merge your-feature-branch
git push origin Version-0.1

# Option 2: Manual workflow dispatch
# Go to: GitHub → Actions → "Build and deploy Python app to Azure Web App - artigen" → Run workflow
```

## Azure App Service Configuration

### Required Environment Variables

Configure these in Azure Portal → Your App Service → Configuration → Application settings:

#### Essential Variables:
```
SECRET_KEY=<your-secret-key>              # Generate with: openssl rand -hex 32
GROQ_API_KEY=<your-groq-api-key>          # From https://console.groq.com/keys
QDRANT_URL=<your-qdrant-url>              # Your Qdrant instance URL
QDRANT_API_KEY=<your-qdrant-api-key>      # If using Qdrant Cloud
```

#### Optional Variables:
```
DATABASE_URL=<postgresql-url>              # Default: SQLite (in-memory)
CORS_ORIGINS=https://yourdomain.com       # Comma-separated origins
ENVIRONMENT=production                     # Set to production
OPENAI_API_KEY=<your-openai-api-key>      # Optional fallback
```

### Startup Configuration

The workflow automatically configures the startup command:
```bash
bash startup.sh
```

This script:
- Changes to the `backend/` directory
- Starts the application using Gunicorn with Uvicorn workers
- Uses the `PORT` environment variable set by Azure (default: 8000)
- Installs spaCy language model in the background (for semantic chunking)

## Application Structure

```
ArtigenAI/
├── backend/
│   ├── app/              # FastAPI application
│   │   ├── main.py       # Serves both API and static frontend
│   │   ├── api/          # API routes
│   │   └── ...
│   ├── static/           # Frontend build output (created during deployment)
│   ├── requirements.txt  # Python dependencies
│   └── ...
├── frontend/
│   ├── src/              # React source code
│   ├── dist/             # Built frontend (excluded from deployment)
│   └── ...
├── startup.sh            # Azure startup script
└── .deployment           # Azure deployment config
```

## Accessing Your Application

After successful deployment:

- **Application URL:** `https://artigen.azurewebsites.net`
- **Health Check:** `https://artigen.azurewebsites.net/health`
- **API Docs:** `https://artigen.azurewebsites.net/docs`
- **Admin Panel:** `https://artigen.azurewebsites.net/admin/login`

### Default Admin Credentials

⚠️ **Important:** Change these immediately after first deployment!

```
Username: admin
Password: admin123
```

## Monitoring and Troubleshooting

### Viewing Logs

**Azure Portal:**
1. Go to your App Service → Log stream
2. Or use: Monitoring → Logs → App Service Application Logs

**Azure CLI:**
```bash
# Stream live logs
az webapp log tail --name artigen --resource-group <your-resource-group>

# Download logs
az webapp log download --name artigen --resource-group <your-resource-group>
```

### Common Issues

#### 1. Deployment Fails During Frontend Build

**Symptoms:** `npm ci` or `npm run build` fails

**Solution:**
- Check frontend dependencies in `frontend/package.json`
- Ensure Node.js 18 is specified in workflow
- Check workflow logs for specific npm errors

#### 2. Application Won't Start

**Symptoms:** HTTP 503 errors, "Application Error" page

**Solutions:**
- Check Application Insights or Log Stream for startup errors
- Verify all required environment variables are set
- Ensure `startup.sh` is executable (should be committed with +x permission)
- Verify Gunicorn is in requirements.txt

#### 3. Frontend Doesn't Load

**Symptoms:** API works but frontend shows 404 or blank page

**Solutions:**
- Verify frontend was built: Check workflow logs for "Build frontend" step
- Ensure static files were copied to `backend/static/`
- Check FastAPI is configured to serve static files (see `app/main.py`)
- Verify the build output is in the deployment artifact

#### 4. Database Errors

**Symptoms:** 500 errors, database connection failures

**Solutions:**
- For production, use PostgreSQL instead of SQLite
- Set `DATABASE_URL` environment variable with PostgreSQL connection string
- Ensure database exists and credentials are correct
- Database is auto-initialized on first startup

#### 5. Qdrant Connection Errors

**Symptoms:** Search/query features don't work

**Solutions:**
- Verify `QDRANT_URL` and `QDRANT_API_KEY` are correct
- Ensure Qdrant instance is accessible from Azure
- Check Qdrant health: `https://your-qdrant-url/healthz`
- See [CONFIGURE_QDRANT.md](CONFIGURE_QDRANT.md) for Qdrant setup

### Health Check Endpoint

The application includes a health check endpoint:

```bash
curl https://artigen.azurewebsites.net/health
```

Expected response:
```json
{
  "status": "healthy"
}
```

### Detailed System Health

For authenticated admin users:

```bash
curl -H "Authorization: Bearer <your-token>" \
     https://artigen.azurewebsites.net/api/admin/health
```

This provides detailed health information about:
- Qdrant connection status
- Database status
- System resources

## Scaling Considerations

### Current Configuration

- **Workers:** 4 Gunicorn workers (configured in startup.sh)
- **Timeout:** 120 seconds per request
- **Plan:** Basic or Standard tier (check Azure Portal)

### Recommendations for Production

**For 1,000+ users:**
- Upgrade to **S1** (Standard) or higher plan
- Enable **Application Insights** for monitoring
- Configure **Auto-scale** rules based on CPU/memory

**For 10,000+ users:**
- Upgrade to **P1V2** (Premium) or higher plan
- Use **PostgreSQL** instead of SQLite
- Enable **Auto-scale** with 2-10 instances
- Consider using **Azure CDN** for static assets
- Implement **Redis** for caching (optional)

For detailed scaling guidance, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Security Best Practices

### Post-Deployment Security Checklist

- [ ] Change default admin credentials
- [ ] Set strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
- [ ] Configure CORS origins to your domain only
- [ ] Enable HTTPS (automatic with Azure App Service)
- [ ] Disable debug mode (ensure `ENVIRONMENT=production`)
- [ ] Set up Application Insights for monitoring
- [ ] Configure backup and disaster recovery
- [ ] Review and rotate API keys regularly

### Updating Secrets

To update environment variables:

```bash
# Using Azure CLI
az webapp config appsettings set \
  --name artigen \
  --resource-group <your-resource-group> \
  --settings SECRET_KEY=<new-value>
```

Or use Azure Portal → Configuration → Application settings

## Updating the Application

### Regular Updates

1. Make changes to your code
2. Commit and push to a feature branch
3. Test locally
4. Merge to `Version-0.1` branch
5. Push to GitHub - deployment triggers automatically

```bash
git checkout Version-0.1
git merge main  # or your feature branch
git push origin Version-0.1
```

### Rollback to Previous Version

If deployment fails or has issues:

```bash
# In Azure Portal
# Go to: Deployment Center → Deployment history → Select previous version → Redeploy
```

Or re-run a previous successful workflow from GitHub Actions.

## Additional Resources

- **Azure App Service Documentation:** https://docs.microsoft.com/en-us/azure/app-service/
- **GitHub Actions for Azure:** https://github.com/Azure/actions
- **Gunicorn Documentation:** https://docs.gunicorn.org/
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/

## Support

For deployment issues:
1. Check the troubleshooting section above
2. Review Azure App Service logs
3. Check GitHub Actions workflow logs
4. See main [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment guide
5. See [README.md](README.md) for application documentation

---

**Last Updated:** Based on workflow version using Python 3.11, Node 18, and Gunicorn deployment.
