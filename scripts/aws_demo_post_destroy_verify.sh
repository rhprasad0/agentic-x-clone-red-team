#!/usr/bin/env bash
set -euo pipefail

PROJECT_TAG_VALUE="${PROJECT_TAG_VALUE:-x-clone}"
ENVIRONMENT_TAG_VALUE="${ENVIRONMENT_TAG_VALUE:-demo}"
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-xclone-demo}"
RECEIPT_DIR="${RECEIPT_DIR:-.hermes/tmp/aws-demo-receipts}"

mkdir -p "$RECEIPT_DIR"
REPORT="$RECEIPT_DIR/post-destroy-verification.md"
: > "$REPORT"

redact() {
  sed -E \
    -e 's/[0-9]{12}/[REDACTED_ACCOUNT]/g' \
    -e 's#arn:aws:[A-Za-z0-9:/._+=,@-]+#[REDACTED_ARN]#g' \
    -e 's#([A-Za-z]:)?/(home|Users)/[A-Za-z0-9._-]+(/[^[:space:]]*)?#[REDACTED_LOCAL_PATH]#g'
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

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 2
  }
}

require_cmd aws
require_cmd python3

cat >> "$REPORT" <<EOF
# x-clone AWS demo post-destroy verification

Expected end state: no active demo EKS cluster, tagged ALBs/NLBs, NAT gateways,
RDS instances, unattached volumes, or avoidable snapshots remain for the demo tag
set. This file is local/private by default; redact and excerpt before publishing.

- project tag: $PROJECT_TAG_VALUE
- environment tag: $ENVIRONMENT_TAG_VALUE
- region: $AWS_REGION
- cluster name: $CLUSTER_NAME
EOF

set +e
EKS_JSON=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json 2>&1)
EKS_RC=$?
set -e
{
  printf '\n## EKS cluster lookup\n\n```text\n'
  if [ "$EKS_RC" -eq 0 ]; then
    echo "$EKS_JSON" | redact
  else
    echo "cluster not found or inaccessible (expected after destroy)" | redact
  fi
  printf '```\n'
} >> "$REPORT"

section "Load balancers tagged for demo" aws resourcegroupstaggingapi get-resources \
  --region "$AWS_REGION" \
  --tag-filters "Key=Project,Values=$PROJECT_TAG_VALUE" "Key=Environment,Values=$ENVIRONMENT_TAG_VALUE" \
  --resource-type-filters elasticloadbalancing:loadbalancer \
  --output json

section "NAT gateways tagged for demo" aws ec2 describe-nat-gateways \
  --region "$AWS_REGION" \
  --filter "Name=tag:Project,Values=$PROJECT_TAG_VALUE" "Name=tag:Environment,Values=$ENVIRONMENT_TAG_VALUE" \
  --output json

section "RDS DB instances tagged for demo" aws resourcegroupstaggingapi get-resources \
  --region "$AWS_REGION" \
  --tag-filters "Key=Project,Values=$PROJECT_TAG_VALUE" "Key=Environment,Values=$ENVIRONMENT_TAG_VALUE" \
  --resource-type-filters rds:db \
  --output json

section "Unattached EBS volumes tagged for demo" aws ec2 describe-volumes \
  --region "$AWS_REGION" \
  --filters "Name=status,Values=available" "Name=tag:Project,Values=$PROJECT_TAG_VALUE" "Name=tag:Environment,Values=$ENVIRONMENT_TAG_VALUE" \
  --output json

section "Snapshots tagged for demo" aws ec2 describe-snapshots \
  --region "$AWS_REGION" \
  --owner-ids self \
  --filters "Name=tag:Project,Values=$PROJECT_TAG_VALUE" "Name=tag:Environment,Values=$ENVIRONMENT_TAG_VALUE" \
  --output json

section "CloudWatch log groups tagged for demo" aws logs describe-log-groups \
  --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME" \
  --output json

cat <<EOF
Post-destroy verification receipt written to $REPORT.
Review any listed resources manually before considering teardown complete.
EOF
