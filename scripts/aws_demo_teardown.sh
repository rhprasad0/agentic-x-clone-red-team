#!/usr/bin/env bash
set -euo pipefail

PROJECT_TAG_VALUE="${PROJECT_TAG_VALUE:-x-clone}"
ENVIRONMENT_TAG_VALUE="${ENVIRONMENT_TAG_VALUE:-demo}"
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-xclone-demo}"
NAMESPACE="${NAMESPACE:-xclone}"
TF_DIR="${TF_DIR:-infra/aws-demo/terraform}"
RECEIPT_DIR="${RECEIPT_DIR:-.hermes/tmp/aws-demo-receipts}"
DESTROY_APPROVAL="${DESTROY_APPROVAL:-dry-run}"
WAIT_SECONDS="${WAIT_SECONDS:-600}"

mkdir -p "$RECEIPT_DIR"

redact() {
  sed -E \
    -e 's/[0-9]{12}/[REDACTED_ACCOUNT]/g' \
    -e 's#arn:aws:[A-Za-z0-9:/._+=,@-]+#[REDACTED_ARN]#g' \
    -e 's#([A-Za-z]:)?/(home|Users)/[A-Za-z0-9._-]+(/[^[:space:]]*)?#[REDACTED_LOCAL_PATH]#g'
}

run_receipt() {
  local label="$1"
  shift
  {
    printf '\n## %s\n\n' "$label"
    printf '```text\n$'
    for arg in "$@"; do printf ' %q' "$arg"; done
    printf '\n'
    "$@" 2>&1 | redact || true
    printf '```\n'
  } >> "$RECEIPT_DIR/teardown-receipt.md"
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 2
  }
}

need aws
need terraform

cat > "$RECEIPT_DIR/teardown-receipt.md" <<EOF
# x-clone AWS demo teardown receipt

This receipt is local/private by default. Review and redact before copying any
small excerpt into public evidence.

- project tag: $PROJECT_TAG_VALUE
- environment tag: $ENVIRONMENT_TAG_VALUE
- region: $AWS_REGION
- cluster name: $CLUSTER_NAME
- namespace: $NAMESPACE
- mode: $DESTROY_APPROVAL
EOF

if command -v kubectl >/dev/null 2>&1; then
  run_receipt "Current Kubernetes context" kubectl config current-context
  run_receipt "Suspend runner CronJobs" kubectl -n "$NAMESPACE" patch cronjob --all -p '{"spec":{"suspend":true}}'
  run_receipt "Delete public Ingresses before ALB cleanup" kubectl -n "$NAMESPACE" delete ingress --all --ignore-not-found=true
  run_receipt "Wait for Ingress deletion" kubectl -n "$NAMESPACE" wait --for=delete ingress --all --timeout="${WAIT_SECONDS}s"
else
  echo "kubectl not found; skipping Kubernetes pre-destroy cleanup." >> "$RECEIPT_DIR/teardown-receipt.md"
fi

if [ ! -d "$TF_DIR" ]; then
  echo "Terraform directory not found: $TF_DIR" >&2
  echo "Create or point TF_DIR at the demo Terraform root before destroy." >&2
  exit 3
fi

terraform -chdir="$TF_DIR" init -input=false
terraform -chdir="$TF_DIR" plan -destroy -out=tfplan.destroy
terraform -chdir="$TF_DIR" show -no-color tfplan.destroy | redact > "$RECEIPT_DIR/terraform-destroy-plan.redacted.txt"

if [ "$DESTROY_APPROVAL" != "destroy-xclone-demo" ]; then
  cat <<EOF
Dry-run complete. Review:
- $RECEIPT_DIR/teardown-receipt.md
- $RECEIPT_DIR/terraform-destroy-plan.redacted.txt

To actually destroy, rerun with DESTROY_APPROVAL=destroy-xclone-demo.
EOF
  exit 0
fi

terraform -chdir="$TF_DIR" apply -auto-approve tfplan.destroy 2>&1 | redact | tee "$RECEIPT_DIR/terraform-destroy-apply.redacted.txt"

./scripts/aws_demo_post_destroy_verify.sh
