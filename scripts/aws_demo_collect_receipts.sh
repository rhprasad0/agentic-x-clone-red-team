#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-xclone-demo}"
NAMESPACE="${NAMESPACE:-xclone}"
FRONTEND_URL="${FRONTEND_URL:-https://xclone.example.com}"
API_URL="${API_URL:-https://api.xclone.example.com}"
ALB_LOG_BUCKET="${ALB_LOG_BUCKET:-}"
ALB_LOG_PREFIX="${ALB_LOG_PREFIX:-alb/xclone-demo}"
RECEIPT_DIR="${RECEIPT_DIR:-.hermes/tmp/aws-demo-receipts}"

mkdir -p "$RECEIPT_DIR"
REPORT="$RECEIPT_DIR/observability-receipts.md"
: > "$REPORT"

redact() {
  sed -E \
    -e 's/[0-9]{12}/[REDACTED_ACCOUNT]/g' \
    -e 's#arn:aws:[A-Za-z0-9:/._+=,@-]+#[REDACTED_ARN]#g' \
    -e 's#([A-Za-z]:)?/(home|Users)/[A-Za-z0-9._-]+(/[^[:space:]]*)?#[REDACTED_LOCAL_PATH]#g' \
    -e 's/(Authorization: Bearer )[A-Za-z0-9._~+\/-]+/\1[REDACTED_BEARER]/Ig'
}

section() {
  local title="$1"
  shift
  {
    printf '\n## %s\n\n```text\n$' "$title"
    for arg in "$@"; do printf ' %q' "$arg"; done
    printf '\n'
    "$@" 2>&1 | redact || true
    printf '```\n'
  } >> "$REPORT"
}

cat >> "$REPORT" <<EOF
# x-clone AWS demo observability receipts

This receipt is local/private by default. It captures class-level deployment and
health evidence for a temporary synthetic demo. Do not commit raw output unless
it has been reviewed, redacted, and scanned.

- region: $AWS_REGION
- cluster name: $CLUSTER_NAME
- namespace: $NAMESPACE
- frontend URL: $FRONTEND_URL
- API URL: $API_URL
EOF

if command -v curl >/dev/null 2>&1; then
  section "Frontend HTTP smoke" curl -fsSI "$FRONTEND_URL"
  section "API health smoke" curl -fsS "$API_URL/health"
  section "Public timeline smoke" curl -fsS "$API_URL/timelines/public?limit=3"
  section "Public unauthenticated post denied smoke" curl -fsSI -X POST "$API_URL/posts"
  section "Public signup denied smoke" curl -fsSI -X POST "$API_URL/agents/signup"
  section "Public export denied smoke" curl -fsSI -X POST "$API_URL/exports/public-evidence"
  section "Public docs disabled smoke" curl -fsSI "$API_URL/docs"
  section "OpenAPI disabled smoke" curl -fsSI "$API_URL/openapi.json"
fi

if command -v kubectl >/dev/null 2>&1; then
  section "Kubernetes pods" kubectl -n "$NAMESPACE" get pods -o wide
  section "Kubernetes ingress" kubectl -n "$NAMESPACE" get ingress -o wide
  section "Recent warning events" kubectl -n "$NAMESPACE" get events --sort-by=.lastTimestamp --field-selector type=Warning
  section "Backend recent logs" kubectl -n "$NAMESPACE" logs deploy/backend --tail=80
  section "Frontend recent logs" kubectl -n "$NAMESPACE" logs deploy/frontend --tail=80
  section "Runner CronJobs" kubectl -n "$NAMESPACE" get cronjob -o wide
fi

if command -v aws >/dev/null 2>&1; then
  section "EKS cluster logging state" aws eks describe-cluster \
    --region "$AWS_REGION" \
    --name "$CLUSTER_NAME" \
    --query 'cluster.logging.clusterLogging' \
    --output json

  section "EKS control-plane log groups" aws logs describe-log-groups \
    --region "$AWS_REGION" \
    --log-group-name-prefix "/aws/eks/$CLUSTER_NAME" \
    --output json

  section "Recent authenticator control-plane logs" aws logs tail \
    "/aws/eks/$CLUSTER_NAME/cluster" \
    --region "$AWS_REGION" \
    --since 30m \
    --filter-pattern 'authenticator' \
    --format short

  if [ -n "$ALB_LOG_BUCKET" ]; then
    section "ALB access log objects" aws s3 ls "s3://$ALB_LOG_BUCKET/$ALB_LOG_PREFIX/" --recursive --summarize
  else
    {
      printf '\n## ALB access log objects\n\n'
      printf 'Skipped: set ALB_LOG_BUCKET to inspect access-log delivery.\n'
    } >> "$REPORT"
  fi
fi

cat <<EOF
Observability receipt written to $REPORT.
Keep it private by default; publish only sanitized excerpts.
EOF
