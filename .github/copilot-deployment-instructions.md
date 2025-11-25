---
description: Deployment and infrastructure guidelines for MagicToolbox
applyTo: '{docker/**,kubernetes/**,terraform/**,*.dockerfile,docker-compose.yml,.github/workflows/**}'
---

# Deployment & Infrastructure Guidelines

## Docker Best Practices

### Backend Dockerfile
- Use official Python slim images
- Multi-stage builds for smaller images
- Run as non-root user
- Cache dependencies separately
- Use .dockerignore to exclude unnecessary files

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Copy application code
COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
- Use Node.js for build stage
- Nginx for serving static files
- Optimize nginx configuration
- Enable gzip compression
- Implement proper caching headers

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose
- Separate dev and prod configurations
- Use environment files
- Define health checks
- Set resource limits
- Use named volumes

```yaml
# docker-compose.yml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/magictoolbox
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - upload-storage:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: magictoolbox
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M

volumes:
  postgres-data:
  redis-data:
  upload-storage:
```

## Kubernetes Deployment

### Backend Deployment
- Use deployments for stateless apps
- Configure resource requests/limits
- Implement liveness and readiness probes
- Use ConfigMaps for configuration
- Use Secrets for sensitive data

```yaml
# kubernetes/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: magictoolbox-backend
  labels:
    app: magictoolbox
    component: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: magictoolbox
      component: backend
  template:
    metadata:
      labels:
        app: magictoolbox
        component: backend
    spec:
      containers:
      - name: backend
        image: magictoolbox/backend:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: magictoolbox-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: magictoolbox-config
              key: redis-url
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: upload-storage
          mountPath: /app/uploads
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: upload-storage-pvc
```

### Service Configuration
- Use ClusterIP for internal services
- Use LoadBalancer or Ingress for external access
- Configure session affinity if needed

```yaml
# kubernetes/backend-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: magictoolbox-backend
  labels:
    app: magictoolbox
    component: backend
spec:
  type: ClusterIP
  selector:
    app: magictoolbox
    component: backend
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  sessionAffinity: None
```

### Ingress Configuration
- Use cert-manager for TLS certificates
- Configure rate limiting
- Implement proper CORS headers
- Set up URL rewrites if needed

```yaml
# kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: magictoolbox-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/enable-cors: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - magictoolbox.example.com
    secretName: magictoolbox-tls
  rules:
  - host: magictoolbox.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: magictoolbox-backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: magictoolbox-frontend
            port:
              number: 80
```

## CI/CD Pipeline (GitHub Actions)

### Build and Test Pipeline
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run tests
      working-directory: ./backend
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: ./frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Run linter
      working-directory: ./frontend
      run: npm run lint
    
    - name: Run tests
      working-directory: ./frontend
      run: npm run test:coverage
    
    - name: Build
      working-directory: ./frontend
      run: npm run build

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy results to GitHub Security
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'
```

### Deployment Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    tags:
      - 'v*'

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ghcr.io/${{ github.repository }}
        tags: |
          type=ref,event=branch
          type=semver,pattern={{version}}
          type=sha
    
    - name: Build and push backend
      uses: docker/build-push-action@v5
      with:
        context: ./backend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
    
    - name: Build and push frontend
      uses: docker/build-push-action@v5
      with:
        context: ./frontend
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up kubectl
      uses: azure/setup-kubectl@v3
    
    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=./kubeconfig
    
    - name: Deploy to Kubernetes
      run: |
        kubectl apply -f kubernetes/
        kubectl rollout status deployment/magictoolbox-backend
        kubectl rollout status deployment/magictoolbox-frontend
```

## Infrastructure as Code (Terraform)

### Provider Configuration
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.6"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "magictoolbox-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "MagicToolbox"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

## Monitoring & Logging

### Health Check Endpoints
- Implement `/health` for liveness checks
- Implement `/ready` for readiness checks
- Include dependency status in ready endpoint
- Return appropriate HTTP status codes

### Structured Logging
- Use JSON format for logs
- Include correlation IDs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Never log sensitive data
- Centralize logs (CloudWatch, Datadog, etc.)

### Metrics Collection
- Expose Prometheus metrics endpoint
- Track request rates, latency, errors
- Monitor resource usage (CPU, memory)
- Set up alerts for critical metrics

## Security Checklist
- [ ] All images scanned for vulnerabilities
- [ ] Secrets stored in secret management system
- [ ] TLS certificates configured and auto-renewed
- [ ] Network policies configured in Kubernetes
- [ ] RBAC properly configured
- [ ] Resource limits set on all containers
- [ ] Non-root users in containers
- [ ] Regular security updates applied
- [ ] Backup and disaster recovery plan in place
- [ ] Monitoring and alerting configured
