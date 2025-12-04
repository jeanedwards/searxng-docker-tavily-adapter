# Azure Container Apps Deployment Guide

## Quick Reference

This document provides a step-by-step checklist for deploying the Tavily Adapter to Azure Container Apps.

## Architecture

The deployment uses Azure Container Apps with a sidecar pattern:
- **Main container**: Tavily Adapter (port 8001, publicly accessible via HTTPS)
- **Sidecar 1**: Redis/Valkey (port 6379, localhost only)
- **Sidecar 2**: SearXNG (port 8080, localhost only)

All three containers share the localhost network within the same Container App instance.

## Deployment Checklist

### 1. Prerequisites

- [ ] Azure subscription with permissions to create resources
- [ ] Resource Group: `RG-GBLI-AI-Risk-Insights` created in Azure
- [ ] Azure Service Principal with Contributor role on the resource group
- [ ] GitHub repository forked or cloned with admin access

### 2. Create Azure Service Principal

```bash
# Create a service principal with Contributor role
az ad sp create-for-rbac \
  --name "searxng-tavily-deployer" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/RG-GBLI-AI-Risk-Insights \
  --sdk-auth

# Copy the entire JSON output for the next step
```

### 3. Configure GitHub Secrets

Navigate to your GitHub repository: **Settings → Secrets and variables → Actions → New repository secret**

Create the following secrets:

#### AZURE_CREDENTIALS
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

#### CONFIG_YAML
Copy the contents of `config.azure.yaml` after editing:

```bash
# Generate and update the secret_key first
RANDOM_KEY=$(openssl rand -hex 32)
sed -i.bak "s/CHANGE_ME_TO_RANDOM_SECRET_KEY_32_CHARS_OR_MORE/$RANDOM_KEY/" config.azure.yaml

# Copy the entire file content to this secret
cat config.azure.yaml
```

#### SEARXNG_SECRET_KEY
Generate a random secret for SearXNG:

```bash
# Generate a random 32-character hex string
openssl rand -hex 32

# Copy the output to this secret
```

### 4. Deploy to Azure

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Deploy to Azure Container Apps** workflow
4. Click **Run workflow** dropdown
5. Select branch: `master` (or your default branch)
6. Click **Run workflow** button
7. Wait for deployment to complete (~5-10 minutes)

### 5. Verify Deployment

```bash
# Get the application URL
az containerapp show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights \
  --query properties.configuration.ingress.fqdn \
  -o tsv

# Test health endpoint
curl https://<your-app-url>/health

# Expected response:
# {"status":"ok","timestamp":"..."}

# Test search endpoint
curl -X POST https://<your-app-url>/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Azure Container Apps","max_results":3}'

# Expected: JSON response with search results
```

### 6. Monitor and Troubleshoot

```bash
# View container app status
az containerapp show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights

# View logs from the main container
az containerapp logs show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights \
  --container tavily-adapter \
  --tail 100

# View logs from Redis sidecar
az containerapp logs show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights \
  --container redis \
  --tail 50

# View logs from SearXNG sidecar
az containerapp logs show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights \
  --container searxng \
  --tail 50

# Check replica status
az containerapp replica list \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights
```

### 7. Update Deployment

To update the deployment with new code or configuration:

1. Push changes to the Docker image:
   ```bash
   # The docker-publish.yml workflow will automatically build and push
   # when you commit to master branch
   ```

2. Update configuration:
   - Edit the `CONFIG_YAML` GitHub secret with new settings
   - Re-run the deployment workflow

3. Trigger redeployment:
   - Go to **Actions → Deploy to Azure Container Apps → Run workflow**

## Configuration Changes

### Updating Environment-Specific Settings

The workflow is configured via environment variables in `.github/workflows/azure-deploy.yml`:

```yaml
env:
  RESOURCE_GROUP: RG-GBLI-AI-Risk-Insights
  CONTAINER_APP_NAME: je-tavily-adapter
  CONTAINER_ENV_NAME: je-tavily-env
  LOCATION: westeurope
```

To change these values, edit the workflow file and commit to your repository.

### Updating Container Resources

Edit the YAML configuration in the workflow to adjust CPU/memory:

```yaml
# Main container
resources:
  cpu: 0.5      # Increase if needed
  memory: 1Gi   # Increase if needed

# Redis sidecar
resources:
  cpu: 0.25
  memory: 0.5Gi

# SearXNG sidecar
resources:
  cpu: 0.5
  memory: 1Gi
```

### Updating Scaling Configuration

```yaml
scale:
  minReplicas: 1    # Minimum instances
  maxReplicas: 3    # Maximum instances for auto-scaling
```

## Differences from Docker Compose

| Aspect | Docker Compose | Azure Container Apps |
|--------|----------------|----------------------|
| Networking | Service names (e.g., `searxng:8080`) | Localhost (e.g., `localhost:8080`) |
| Configuration | Volume-mounted `config.yaml` | Injected via environment variable |
| Storage | Persistent volumes | Ephemeral (data lost on restart) |
| Scaling | Manual | Automatic (1-3 replicas) |
| Access | Local network only | HTTPS with Azure-provided domain |
| Cost | Infrastructure cost | Pay-per-use (container apps pricing) |

## Security Considerations

1. **Secrets Management**: Never commit `config.yaml` or secrets to the repository
2. **Network Security**: Only the main container (port 8001) is exposed; sidecars are internal
3. **HTTPS**: Azure Container Apps provides automatic HTTPS with managed certificates
4. **Service Principal**: Limit permissions to the specific resource group only
5. **Configuration**: Store sensitive data in GitHub Secrets, not in the repository

## Cost Estimation

Azure Container Apps pricing (approximate):

- **Consumption plan**: ~$0.000016/vCPU-second + $0.0000018/GB-second
- **Estimated monthly cost** (1 replica running 24/7):
  - CPU: 1.25 vCPU × 2,592,000 seconds × $0.000016 ≈ $52/month
  - Memory: 2.5 GB × 2,592,000 seconds × $0.0000018 ≈ $12/month
  - **Total**: ~$64/month for continuous operation

To reduce costs:
- Set `minReplicas: 0` (scale to zero when idle)
- Use smaller CPU/memory allocations if sufficient
- Consider Azure Free Tier credits if available

## Troubleshooting

### Deployment fails with "ResourceNotFound"

**Solution**: Ensure the resource group exists:
```bash
az group create -n RG-GBLI-AI-Risk-Insights -l westeurope
```

### Application returns 502 Bad Gateway

**Possible causes**:
1. Main container not starting properly
2. Health check failing

**Solution**: Check container logs and verify the health endpoint

### SearXNG not responding

**Possible causes**:
1. SearXNG sidecar failed to start
2. Configuration issues

**Solution**: Check SearXNG sidecar logs and verify environment variables

### "Connection refused" errors in logs

**Possible causes**:
1. Sidecars not ready when main container starts
2. Port mismatch

**Solution**: Add startup delay or health checks for sidecars

## Support

For issues specific to:
- **Azure deployment**: Check Azure Container Apps documentation
- **Application functionality**: Open an issue in the GitHub repository
- **Configuration**: Review `CONFIG_SETUP.md` in the repository

