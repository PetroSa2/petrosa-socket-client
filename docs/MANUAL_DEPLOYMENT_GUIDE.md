# Manual Deployment Guide

This guide explains how to use the manual deployment workflow to deploy petrosa-socket-client without code changes.

## Overview

The manual deployment workflow allows you to:

- **Deploy without code changes**: Trigger deployments for configuration updates, infrastructure changes, or version tracking
- **Version control**: Automatically bump version numbers using semantic versioning (patch/minor/major)
- **Environment selection**: Deploy to staging or production environments
- **Audit trail**: Maintain complete records of who deployed what, when, and why
- **CI/CD validation**: All deployments go through the same validation as code-triggered deployments

## Use Cases

### When to Use Manual Deployment

1. **Configuration Updates**: Deploy with new environment variables without code changes
2. **Infrastructure Changes**: Re-deploy after Kubernetes cluster updates or scaling
3. **Version Tracking**: Create new versions for tracking purposes
4. **Hotfix Deployments**: Deploy urgent fixes that only update manifests
5. **Docker Image Updates**: Push new images with the same codebase
6. **Testing**: Test deployment pipeline without modifying code

### When NOT to Use Manual Deployment

- **Code changes**: Use the standard PR merge workflow instead
- **Breaking changes**: Major refactors should go through normal PR review
- **Untested changes**: All changes should be tested before manual deployment

## Prerequisites

- Access to the GitHub repository with write permissions
- Understanding of semantic versioning (see below)
- Knowledge of target environment (staging vs production)

## Triggering Deployments

### Option 1: GitHub UI (Recommended for Most Users)

1. **Navigate to Actions Tab**
   - Go to: https://github.com/PetroSa2/petrosa-socket-client/actions
   - Find "Manual Deployment with Version Bump" workflow

2. **Click "Run workflow" button** (top right)

3. **Fill in the form**:
   - **Target environment**: Choose `staging` or `production`
     - `staging`: For testing changes before production
     - `production`: For live deployment to production cluster
   
   - **Version bump type**: Choose `patch`, `minor`, or `major`
     - `patch`: Bug fixes, small changes (1.0.0 → 1.0.1)
     - `minor`: New features, backward-compatible (1.0.0 → 1.1.0)
     - `major`: Breaking changes, major updates (1.0.0 → 2.0.0)
   
   - **Reason for deployment**: Provide a clear explanation
     - Example: "Updated NATS connection timeout configuration"
     - Example: "Re-deploy after Kubernetes cluster upgrade"
     - Example: "Hotfix: Increased memory limits for production stability"

4. **Click "Run workflow"** to start deployment

5. **Monitor Progress**
   - Watch the workflow execution in real-time
   - Check each step for success/failure
   - Review deployment verification output

### Option 2: GitHub CLI (Advanced Users)

```bash
# Install GitHub CLI if not already installed
# macOS: brew install gh
# Linux: See https://github.com/cli/cli#installation

# Authenticate (first time only)
gh auth login

# Trigger deployment to staging with patch version bump
gh workflow run "Manual Deployment with Version Bump" \
  --ref main \
  -f environment=staging \
  -f version_bump=patch \
  -f reason="Updated connection retry configuration"

# Trigger deployment to production with minor version bump
gh workflow run "Manual Deployment with Version Bump" \
  --ref main \
  -f environment=production \
  -f version_bump=minor \
  -f reason="New feature: Enhanced error handling"

# Check workflow run status
gh run list --workflow="Manual Deployment with Version Bump"

# View detailed logs
gh run view <run-id> --log
```

## Semantic Versioning Guide

The workflow uses semantic versioning (semver) format: `vMAJOR.MINOR.PATCH`

### Version Components

- **MAJOR**: Breaking changes, incompatible API changes
  - Example: `v1.5.3 → v2.0.0`
  - When: Database schema changes, API redesign, major refactoring

- **MINOR**: New features, backward-compatible additions
  - Example: `v1.5.3 → v1.6.0`
  - When: New endpoints, new configuration options, feature additions

- **PATCH**: Bug fixes, minor changes
  - Example: `v1.5.3 → v1.5.4`
  - When: Bug fixes, configuration tweaks, performance improvements

### Examples

| Current Version | Bump Type | New Version | Use Case |
|----------------|-----------|-------------|----------|
| v1.0.40 | patch | v1.0.41 | Fixed memory leak in connection handler |
| v1.0.40 | minor | v1.1.0 | Added support for new Binance streams |
| v1.0.40 | major | v2.0.0 | Redesigned message format (breaking) |
| v1.2.5 | patch | v1.2.6 | Updated retry timeout configuration |
| v1.2.5 | minor | v1.3.0 | Added health check endpoint |

## Deployment Workflow Steps

When you trigger a manual deployment, the following steps occur:

1. **Version Bump**
   - Gets current version from git tags
   - Increments version based on bump type
   - Example: v1.0.40 + patch = v1.0.41

2. **Git Tag Creation**
   - Creates annotated git tag with deployment reason
   - Pushes tag to GitHub repository
   - Tag format: `v1.0.41`

3. **Docker Image Build**
   - Builds Docker image with new version tag
   - Includes version metadata in image labels
   - Uses buildx for multi-platform support

4. **Docker Image Push**
   - Pushes image to Docker Hub registry
   - Tags: `yurisa2/petrosa-socket-client:v1.0.41`
   - Also updates `latest` tag

5. **Kubernetes Deployment**
   - Updates deployment manifests with new version
   - Applies manifests to target namespace
   - Uses `--insecure-skip-tls-verify` for external cluster

6. **Rollout Verification**
   - Waits for deployment to be ready (5 min timeout)
   - Verifies pods are running
   - Checks service and ingress status

7. **Deployment Summary**
   - Displays deployment information
   - Shows who triggered, when, and why
   - Provides verification commands

## Audit Trail

Every manual deployment is fully auditable:

### GitHub Actions Logs
- Full execution logs for each deployment
- Timestamp: When deployment was triggered
- Actor: Who triggered the deployment
- Reason: Why the deployment was triggered
- Environment: Which environment was targeted
- Version: Which version was deployed

### Git History
- Git tags show version history
- Tag annotations include deployment reason
- Commit history shows when tags were created

### Kubernetes Events
- Deployment events in Kubernetes
- Pod creation/deletion events
- Rollout status changes

## Troubleshooting

### Common Issues

#### 1. "Current version not found"
**Problem**: No git tags exist in repository

**Solution**:
```bash
# Create initial tag
git tag v1.0.0
git push origin v1.0.0
```

#### 2. "Docker login failed"
**Problem**: Invalid Docker Hub credentials

**Solution**:
- Verify `DOCKERHUB_USERNAME` secret is set
- Verify `DOCKERHUB_TOKEN` secret is valid and not expired
- Generate new token: https://hub.docker.com/settings/security

#### 3. "kubectl connection failed"
**Problem**: Invalid or expired Kubernetes credentials

**Solution**:
- Verify `KUBE_CONFIG_DATA` secret is current
- Check cluster is accessible: `kubectl cluster-info`
- Verify external IP is reachable: `15.235.72.170:35902`

#### 4. "Deployment timeout"
**Problem**: Deployment didn't complete within 5 minutes

**Solution**:
```bash
# Check pod status
kubectl get pods -n petrosa-apps -l app=socket-client

# Check pod logs
kubectl logs -n petrosa-apps -l app=socket-client --tail=50

# Check events
kubectl get events -n petrosa-apps --sort-by='.lastTimestamp'
```

#### 5. "Image pull failed"
**Problem**: Kubernetes can't pull Docker image

**Solution**:
- Verify image exists: `docker pull yurisa2/petrosa-socket-client:v1.0.41`
- Check image registry secret is configured
- Verify network connectivity from cluster to Docker Hub

### Verification Commands

```bash
# Check deployment status
kubectl get deployment petrosa-socket-client -n petrosa-apps

# Check running pods
kubectl get pods -n petrosa-apps -l app=socket-client

# Check deployed image version
kubectl get deployment petrosa-socket-client -n petrosa-apps -o jsonpath='{.spec.template.spec.containers[0].image}'

# View pod logs
kubectl logs -n petrosa-apps -l app=socket-client --tail=100

# Check service endpoints
kubectl get svc petrosa-socket-client-service -n petrosa-apps

# Check ingress
kubectl get ingress petrosa-socket-client-ingress -n petrosa-apps
```

### Getting Help

If you encounter issues not covered here:

1. **Check GitHub Actions logs**: Full execution details
2. **Review Kubernetes events**: `kubectl get events -n petrosa-apps`
3. **Check application logs**: `kubectl logs -n petrosa-apps -l app=socket-client`
4. **Contact DevOps team**: Provide workflow run ID and error details

## Best Practices

### Deployment Strategy

1. **Always test in staging first**
   - Deploy to staging environment
   - Verify functionality
   - Monitor for errors
   - Then deploy to production

2. **Use appropriate version bumps**
   - Patch: Most deployments (config changes, small fixes)
   - Minor: New features, significant changes
   - Major: Breaking changes only

3. **Provide clear deployment reasons**
   - Good: "Updated NATS timeout from 5s to 10s to reduce reconnection errors"
   - Bad: "Update config"
   - Good: "Re-deploy after Kubernetes cluster upgrade to v1.28"
   - Bad: "Redeploy"

4. **Monitor after deployment**
   - Watch pod status for 5-10 minutes
   - Check application logs for errors
   - Verify metrics in monitoring system
   - Test key functionality

### Version Management

1. **Keep versions sequential**: Don't skip versions
2. **Don't reuse versions**: Each deployment should increment
3. **Tag format**: Always use `vX.Y.Z` format
4. **Document major changes**: Update CHANGELOG.md for major/minor bumps

### Environment Management

1. **Staging → Production flow**
   - Test all changes in staging
   - Verify success before production
   - Use same version numbers across environments

2. **Rollback strategy**
   - Keep previous versions available
   - Know how to rollback: `kubectl rollout undo`
   - Test rollback procedure periodically

## Examples

### Example 1: Configuration Update

**Scenario**: Increased connection timeout in ConfigMap

**Steps**:
1. Update ConfigMap in Kubernetes cluster
2. Trigger manual deployment:
   - Environment: `staging`
   - Version bump: `patch`
   - Reason: "Increased WebSocket connection timeout from 30s to 60s"
3. Verify pods restart with new configuration
4. Monitor for 10 minutes
5. If successful, repeat for production

### Example 2: Infrastructure Change

**Scenario**: Kubernetes cluster upgraded to new version

**Steps**:
1. After cluster upgrade, trigger redeployment:
   - Environment: `production`
   - Version bump: `patch`
   - Reason: "Re-deploy after Kubernetes cluster upgrade to v1.28"
2. Monitor rollout status
3. Verify all pods are running on new nodes
4. Check application functionality

### Example 3: New Feature Deployment

**Scenario**: Added new metrics endpoint (no code changes to socket-client)

**Steps**:
1. Trigger deployment:
   - Environment: `staging`
   - Version bump: `minor`
   - Reason: "Enable new metrics endpoint in configuration"
2. Test new endpoint in staging
3. If successful, deploy to production:
   - Environment: `production`
   - Version bump: `minor` (use same reason)

## Related Documentation

- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Standard deployment procedures
- [Versioning Guide](./VERSIONING_GUIDE.md) - Version management details
- [Operations Guide](./OPERATIONS_GUIDE.md) - Operational procedures
- [Kubernetes Setup](./KUBERNETES_SETUP.md) - Cluster configuration

## Changelog

- **2025-10-26**: Initial manual deployment workflow implementation
- **Current Version**: Based on proven pattern from petrosa_k8s

---

**Need Help?** Check the [Troubleshooting](#troubleshooting) section or contact the DevOps team.
