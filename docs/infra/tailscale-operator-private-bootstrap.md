# Tailscale Operator private bootstrap

This is the public-safe handoff for bootstrapping the Tailscale Kubernetes Operator credential and tag-policy path for the x-clone EKS demo.

It intentionally contains object names, key names, and placeholder command shapes only. Do not add real Tailscale OAuth client IDs, OAuth client secrets, auth URLs, tailnet names, MagicDNS hostnames, user/device identities, or screenshots to this file.

## Documentation sources checked

- Context7 `/websites/tailscale`: Kubernetes Operator install examples, OAuth credential prerequisites, and tag-owner examples.
- Tailscale Kubernetes Operator Helm chart `values.yaml`: when Helm values do not set `oauth.clientId` / `oauth.clientSecret` and no `oauthSecretVolume` override is used, the chart expects a pre-created Secret named `operator-oauth` in the operator namespace with files/keys named `client_id` and `client_secret`.

Current Tailscale docs say the Kubernetes Operator OAuth client needs the operator tag and write scopes for Devices Core, Auth Keys, and Services. Keep those credentials private and scoped to this demo.

## Chosen private credential path

Use a live, cluster-local Kubernetes Secret for the Tailscale Operator OAuth credentials:

```text
namespace: tailscale
secret: operator-oauth
keys: client_id, client_secret
values: private; never committed
```

Reasoning:

- Flux can own the public HelmRelease and generic operator manifests without storing secrets in Git.
- The live Secret can be created before Flux reconciles the HelmRelease.
- The default chart secret name and key shape keep the public Helm values minimal.
- Revocation is clean: revoke the OAuth client in the Tailscale admin console, delete the Kubernetes Secret, and reconcile/restart the operator.

Do not use Tailscale Funnel for this mutation lane.

## Private admin-console setup

In the Tailscale admin console, create an OAuth client for the Kubernetes Operator with the minimum documented scopes for operator behavior:

```text
scopes: Devices Core write, Auth Keys write, Services write
operator tag: tag:k8s-operator
```

Record the real client ID and secret only in the operator's private password manager or ignored local shell/session. Do not paste either value into the repo, Kanban comments, Slack receipts, screenshots, or terminal logs that may be committed.

## Tailnet policy shape

Add or verify tag ownership privately in the tailnet policy. Public-safe example shape:

```json
{
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

The exact users/groups/admin identities that can edit policy are private tailnet state and should not be committed here.

## Live bootstrap command shape

Run the live bootstrap from a trusted operator shell after loading the real values into environment variables. The command below is intentionally placeholder-only.

```bash
kubectl create namespace tailscale --dry-run=client -o yaml | kubectl apply -f -

kubectl -n tailscale create secret generic operator-oauth \
  --from-literal=client_id="$TAILSCALE_OPERATOR_OAUTH_CLIENT_ID" \
  --from-literal=client_secret="$TAILSCALE_OPERATOR_OAUTH_CLIENT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Before running this, confirm the environment variables are present without printing values:

```bash
test -n "$TAILSCALE_OPERATOR_OAUTH_CLIENT_ID"
test -n "$TAILSCALE_OPERATOR_OAUTH_CLIENT_SECRET"
```

After running it, verify only object/key shape:

```bash
kubectl -n tailscale get secret operator-oauth -o jsonpath='{.metadata.name}{"\n"}'
kubectl -n tailscale get secret operator-oauth -o jsonpath='{.data}' | jq 'keys'
```

Expected key list:

```text
client_id
client_secret
```

Do not print or decode Secret data.

## GitOps reference contract

The public GitOps scaffolding should reference the private Secret by default chart convention rather than embedding OAuth values:

```text
HelmRelease namespace: tailscale
release/chart: tailscale-operator
credential source: pre-created Secret tailscale/operator-oauth
credential keys: client_id, client_secret
```

If a future task switches to workload identity federation or Secrets Store CSI for this operator credential, keep the same rule: commit only object names and placeholder wiring; keep real audience/credential/provider details private unless Ryan explicitly says they are safe to publish.

## Verification receipt shape

A public-safe Kanban or docs receipt may say:

```text
Tailscale credential object exists: yes/no
namespace: tailscale
secret name: operator-oauth
keys present: client_id, client_secret
OAuth values printed: no
private tailnet details printed: no
Funnel enabled: no
```

Do not include real OAuth values, tailnet names, user identities, device identities, auth URLs, home IPs, or MagicDNS hostnames.
