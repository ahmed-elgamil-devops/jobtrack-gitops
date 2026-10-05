#!/usr/bin/env bash
# Creates a local Kubernetes cluster with everything JobTrack needs:
#   kind cluster -> ingress-nginx -> metrics-server -> kube-prometheus-stack -> Argo CD -> JobTrack app
# Requirements: docker, kind, kubectl, helm
set -euo pipefail

CLUSTER=jobtrack
cd "$(dirname "$0")/.."

for bin in docker kind kubectl helm; do
  command -v "$bin" >/dev/null || { echo "Missing: $bin"; exit 1; }
done

echo "==> 1/6 Creating kind cluster"
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --config scripts/kind-config.yaml

echo "==> 2/6 Installing ingress-nginx"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait -n ingress-nginx --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=180s

echo "==> 3/6 Installing metrics-server (needed by the HPA)"
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
helm repo update >/dev/null
helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
  --set args={--kubelet-insecure-tls}

echo "==> 4/6 Installing Prometheus + Grafana (kube-prometheus-stack)"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/kube-prometheus-values.yaml --wait --timeout 10m

echo "==> 5/6 Installing Argo CD"
helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace --wait --timeout 10m

echo "==> 6/6 Deploying JobTrack through Argo CD"
kubectl create namespace jobtrack --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n jobtrack get secret jobtrack-db >/dev/null 2>&1; then
  kubectl -n jobtrack create secret generic jobtrack-db \
    --from-literal=username=jobtrack \
    --from-literal=password="$(openssl rand -base64 24 | tr -d '/+=')" \
    --from-literal=database=jobtrack
fi
kubectl apply -f argocd/application.yaml

cat <<EOF

Done!
  1. Add this line to your hosts file:   127.0.0.1 jobtrack.local
     (Linux/macOS: /etc/hosts, Windows: C:\\Windows\\System32\\drivers\\etc\\hosts)
  2. App:      http://jobtrack.local
  3. Argo CD:  kubectl -n argocd port-forward svc/argocd-server 8081:443  ->  https://localhost:8081
               user: admin  password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
  4. Grafana:  kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80  ->  http://localhost:3000
               user: admin  password: kubectl -n monitoring get secret monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 -d
               Dashboard: "JobTrack"
EOF
