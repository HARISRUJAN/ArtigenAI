# Container Registry Setup

This document describes the GitHub Container Registry (GHCR) setup for the ArtigenAI project.

## Overview

The project is configured to automatically build and push Docker container images to GitHub Container Registry (GHCR). This enables easy deployment to various platforms including Azure Web App Service.

## GitHub Actions Workflow

The workflow file `.github/workflows/build-and-push-container.yml` handles the automated build and push process.

### Workflow Features

- **Automatic Triggers**: Runs on push to main branches (main, master, Version-0.1, copilot/**)
- **Manual Trigger**: Can be triggered manually via GitHub Actions UI (`workflow_dispatch`)
- **Pull Request Builds**: Builds images for pull requests to verify they work
- **Multi-stage Docker Build**: Builds both frontend and backend in a single optimized image
- **Image Tagging**: Automatically tags images with branch names, commit SHAs, and "latest" tag for main branches
- **Build Caching**: Uses GitHub Actions cache to speed up builds

### Container Image Location

Once built and pushed, the container image will be available at:

```
ghcr.io/{owner}/{repo}/aigov-app:<tag>
```

For this repository:
```
ghcr.io/harisrujan/artigenai/aigov-app:<tag>
```

Where `<tag>` can be:
- Branch name (e.g., `version-0.1`, `copilot-add-container-image-registry`)
- Commit SHA (e.g., `version-0.1-0eba68b`)
- `latest` (for main/Version-0.1 branches)

## Using the Container Image

### Pull the image

```bash
# Generic format
docker pull ghcr.io/{owner}/{repo}/aigov-app:latest

# For this repository
docker pull ghcr.io/harisrujan/artigenai/aigov-app:latest
```

### Run the container locally

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="sqlite:///./aigov.db" \
  -e SECRET_KEY="your-secret-key" \
  -e GROQ_API_KEY="your-groq-api-key" \
  -e QDRANT_URL="http://qdrant:6333" \
  ghcr.io/harisrujan/artigenai/aigov-app:latest
```

### Deploy to Azure Web App

The image can be deployed directly to Azure Web App Service using the container deployment method. See `DEPLOYMENT.md` for detailed instructions.

## First-Time Setup

### For Repository Maintainers

The workflow uses the built-in `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets need to be configured for pushing to GHCR.

### For Fork Users

If you've forked this repository:

1. The workflow may require approval to run on first push (GitHub security feature for forks)
2. Go to your repository's "Actions" tab and approve the workflow
3. Subsequent runs will be automatic

### Permissions

The workflow requires the following permissions:
- `contents: read` - To checkout the repository code
- `packages: write` - To push images to GitHub Container Registry

These permissions are configured in the workflow file and are automatically granted by `GITHUB_TOKEN`.

## Image Visibility

By default, container images pushed to GHCR are private. To make them public:

1. Go to https://github.com/users/{USERNAME}/packages (or your organization's packages page)
2. Find the `{repo}/aigov-app` package
3. Click "Package settings"
4. Scroll to "Danger Zone" and change visibility to public

## Troubleshooting

### Workflow not running

- For forked repositories, the workflow may need manual approval on first run
- Check the "Actions" tab for pending approvals

### Build failures

- Check the workflow run logs in the Actions tab
- Ensure all required files exist (frontend/package.json, backend/requirements.txt, etc.)
- Verify the Dockerfile builds locally using: `docker build -f backend/Dockerfile -t test .`

### Permission errors

- Ensure the workflow has `packages: write` permission
- For organization repositories, check organization-level package settings

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment instructions including Azure setup
- [README.md](README.md) - Main project documentation
- [backend/Dockerfile](backend/Dockerfile) - Multi-stage Dockerfile used for building images

## Manual Build and Push

If you need to build and push manually:

```bash
# Build the image from repository root
docker build -f backend/Dockerfile -t ghcr.io/{owner}/{repo}/aigov-app:manual .

# Login to GHCR (replace {USERNAME} with your GitHub username)
echo $GITHUB_TOKEN | docker login ghcr.io -u {USERNAME} --password-stdin

# Push the image
docker push ghcr.io/{owner}/{repo}/aigov-app:manual
```

Replace `{owner}`, `{repo}`, and `{USERNAME}` with your actual values, and `$GITHUB_TOKEN` with a Personal Access Token (PAT) with `write:packages` permission.
