# Deployment.md — Varta Agent on AWS EKS

This guide captures the exact steps and gotchas we hit while deploying **varta-svc-agent** to **Amazon EKS**.

---

## 0) Prerequisites
- **AWS CLI** and **kubectl** installed; **eksctl** recommended.
- An AWS account with permissions to manage EKS, ECR, IAM.
- ECR repository created for the image (e.g., `varta-svc-agent`).

**Reasoning:** These tools and permissions are the foundation; ECR stores images, EKS runs them.

---

## 1) Create / Access the EKS cluster
```bash
# Example cluster
eksctl create cluster \
  --name varta-cluster \
  --region us-east-1 \
  --nodegroup-name varta-nodes \
  --nodes 2 \
  --node-type t3.medium

# Configure kubeconfig
aws eks update-kubeconfig --name varta-cluster --region us-east-1

# Verify
kubectl config current-context
kubectl get nodes -o wide
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.architecture}{"\n"}{end}'
```
**Reasoning:** `update-kubeconfig` wires kubectl auth to EKS; we confirmed nodes are **amd64**.

---

## 2) Build and push the container image (amd64)
**Dockerfile guidance (two safe patterns):**

**A) Poetry without copying a venv** (install site‑packages inside image):
```dockerfile
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --only main
COPY src src
COPY fixtures fixtures

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /usr/local /usr/local
COPY --from=build /app/src ./src
COPY --from=build /app/fixtures ./fixtures
EXPOSE 8090
CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","8090"]
```

**B) Two-stage with in-project venv** (OK if built for correct arch):
```dockerfile
FROM --platform=linux/amd64 python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.in-project true \
 && poetry install --no-root --without dev
COPY src src
COPY fixtures fixtures

FROM --platform=linux/amd64 python:3.12-slim AS production
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/fixtures /app/fixtures
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8090
CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","8090"]
```

**Build & push for amd64 (matches node arch):**
```bash
docker buildx create --use || true
aws ecr get-login-password --region us-east-1 \
 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

export IMAGE=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/varta-svc-agent
export TAG=v0.1.0-6c6a89d  # example

# Important: build for linux/amd64
docker buildx build --platform linux/amd64 -t ${IMAGE}:${TAG} . --push
```
**Reasoning:** Nodes are **amd64**, so images must be **linux/amd64** to avoid `exec format error`.

> **Note on warnings:** If you see a platform mismatch warning, it’s usually due to `DOCKER_DEFAULT_PLATFORM` in your shell. The final image platform must be amd64; the warning itself doesn’t matter once the result is amd64.

---

## 3) ECR pull permissions
**Option A (recommended):** Ensure node IAM role has **AmazonEC2ContainerRegistryReadOnly**.

**Option B:** Create an imagePullSecret and reference it.
```bash
aws ecr get-login-password --region us-east-1 \
| kubectl create secret docker-registry ecr-pull \
  --docker-server=<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS --docker-password-stdin -n varta
```
Then in `values.yaml` (if needed):
```yaml
imagePullSecrets:
  - name: ecr-pull
```
**Reasoning:** Nodes must authenticate to ECR to pull images.

---

## 4) Create Kubernetes namespace and secrets
```bash
kubectl create namespace varta || true

# App secrets example
kubectl -n varta create secret generic agent-secrets \
  --from-literal=API_KEY=abcd1234 \
  --from-literal=DB_PASS=xyz987
```
**Reasoning:** Keep app secrets out of the image; inject at runtime via Kubernetes Secrets.

---

## 5) Helm chart: values.yaml
Minimal working `values.yaml` we used:
```yaml
image:
  repository: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/varta-svc-agent
  tag: "v0.1.0-6c6a89d"   # overridden via --set image.tag=$TAG during deploy
  pullPolicy: IfNotPresent

replicaCount: 1

service:
  port: 8090
  type: ClusterIP

env:
  USE_MOCKS: "true"
  LOG_LEVEL: DEBUG
  CORE_API_BASE: http://localhost:8080/api/v1
  MODEL_NAME: openai:gpt-5
  EMBEDDING_MODEL: sentence-transformers/all-MiniLM-L6-v2
  MAX_TOKENS: "3000"
  TEMPERATURE: "0.3"

envFrom:
  - secretRef:
      name: agent-secrets
```
**Reasoning:** ClusterIP keeps the service private; `envFrom` maps Secret keys to env vars.

---

## 6) Deployment template (key snippet)
Make sure conditional blocks don’t render empty keys. The working container section:
```yaml
containers:
  - name: agent
    image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    ports:
      - containerPort: {{ .Values.service.port }}
        name: http

    {{- with .Values.env }}
    env:
    {{- range $k, $v := . }}
      - name: {{ $k }}
        value: "{{ $v }}"
    {{- end }}
    {{- end }}

    {{- with .Values.envFrom }}
    envFrom:
    {{ toYaml . | nindent 6 }}
    {{- end }}

    # Rely on image CMD/ENTRYPOINT unless you explicitly need overrides
    # command: ["uvicorn"]
    # args: ["src.app:app","--host","0.0.0.0","--port","{{ .Values.service.port }}"]
```
**Reasoning:** `with` prevents empty `env`/`envFrom` blocks, and `nindent` keeps YAML valid.

---

## 7) Install / Upgrade with Helm
Note `TAG` is `0.1.0-${GIT_SHA}` but has to be manually set. 
Note some things like image.repository are hardcoded which needs to be changed.

```bash
helm upgrade --install agent ./charts/varta-svc-agent -n varta \
  --set image.tag=${TAG}
```
Check status and image:
```bash
kubectl -n varta rollout status deploy/varta-svc-agent
kubectl -n varta get deploy varta-svc-agent -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```
**Reasoning:** We pass the tag on the CLI for repeatable, immutable releases per build.

---

## 8) Verify Service & connectivity
```bash
kubectl -n varta get svc varta-svc-agent
kubectl -n varta get endpoints varta-svc-agent -o wide

# Local test via port-forward (private ClusterIP)
kubectl -n varta port-forward svc/varta-svc-agent 8090:8090
curl -s localhost:8090/health || curl -s localhost:8090/
```
**Reasoning:** Endpoints confirm pods match the Service selector; port-forward simulates access.

---

## 9) Troubleshooting checklist
- **No pods created:**
  ```bash
  helm get manifest agent -n varta | grep -nE '^kind: (Deployment|StatefulSet|DaemonSet|Job|CronJob)'
  kubectl -n varta get deploy,sts,ds,job
  ```
  *Reasoning:* Chart may not render workloads if `enabled: false`.

- **Service has no endpoints:**
  ```bash
  kubectl -n varta describe svc varta-svc-agent
  kubectl -n varta get pods --show-labels
  ```
  *Reasoning:* Label/selector mismatch.

- **`exec format error`:** Image arch ≠ node arch.
  ```bash
  docker buildx build --platform linux/amd64 ...
  ```
  *Reasoning:* Ensure image is amd64 for t3.* nodes.

- **ImagePullBackOff:**
  - Node role missing ECR permissions, or missing `imagePullSecrets`.

- **Pending due to resources/taints:**
  ```bash
  kubectl describe pod <pod>
  ```
  *Reasoning:* Requests too high or taints not tolerated.

- **Template/YAML errors (`apiVersion not set`):**
  ```bash
  helm template --debug ./charts/varta-svc-agent -n varta --set image.tag=$TAG > out.yaml
  ```
  *Reasoning:* Empty blocks or bad indentation created blank docs.

- **Watch logs live:**
  ```bash
  kubectl -n varta logs -f deployment/varta-svc-agent
  ```

---

## 10) Versioning & maintenance
- **Cluster version:** If AWS warns about EKS version support windows, plan upgrades (`eksctl upgrade cluster --version <new>`).
- **Node OS/arch:** We used **Amazon Linux 2023 (x86_64)** → matches **linux/amd64** images.

**Reasoning:** Staying within standard support avoids extended-support fees and security risk.

---

## 11) Quick command reference
```bash
# Build & push (amd64)
docker buildx build --platform linux/amd64 -t ${IMAGE}:${TAG} . --push

# Deploy with Helm
target_ns=varta
helm upgrade --install agent ./charts/varta-svc-agent -n $target_ns \
  --set image.repository=${IMAGE} --set image.tag=${TAG}

# Verify
kubectl -n $target_ns rollout status deploy/varta-svc-agent
kubectl -n $target_ns get svc varta-svc-agent
kubectl -n $target_ns get endpoints varta-svc-agent -o wide

# Logs
a=deployment/varta-svc-agent
kubectl -n $target_ns logs -f $a

# Debug templates
helm template --debug agent ./charts/varta-svc-agent -n $target_ns --set image.tag=${TAG} > out.yaml
```

---

**Done.** This is the minimal, repeatable path we used to get `varta-svc-agent` running on EKS with private networking (ClusterIP) and secrets via `envFrom`. Tweak resource requests/limits and autoscaling as you productionize.

