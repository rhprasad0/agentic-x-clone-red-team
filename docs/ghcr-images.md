# GHCR image publishing

This repo publishes two deployable application container images to GitHub Container Registry (GHCR):

- `ghcr.io/rhprasad0/agentic-x-clone-red-team/backend`
- `ghcr.io/rhprasad0/agentic-x-clone-red-team/frontend`

The workflow lives at `.github/workflows/publish-ghcr-images.yml` and runs on pushes to `main`, version tags matching `v*`, and manual `workflow_dispatch` runs.

## Permissions and secrets posture

The workflow uses only the repository-provided `GITHUB_TOKEN`:

- `contents: write` so the post-publish job can pin GitOps image refs back to `main`
- `packages: write` to push GHCR images

No personal access token, cloud credential, package password, or static secret is required. The workflow does not print registry credentials and uses the official Docker login/build/metadata actions.

## Tags

Each image is tagged predictably by Docker metadata rules:

- immutable commit tags: `sha-<short-sha>`
- branch tags for branch builds, currently only `main` by default
- Git tag names for release tags such as `v1.2.3`
- `latest` only for the default branch

Deployment manifests should prefer immutable `sha-<short-sha>` tags or digests once the image digest is captured by the deployment workflow. `latest` is for manual smoke convenience, not a stable deployment contract.

## Public EKS pull behavior

Public GHCR packages can be pulled by EKS nodes without Kubernetes `imagePullSecrets`. This is the preferred demo posture because it avoids carrying registry credentials into the cluster runtime.

Manual GitHub toggle required after first publish:

1. Open the GitHub package page for each image.
2. Change package visibility from private to public.
3. Confirm the package is linked to this repository.
4. Smoke-check an anonymous pull path before assuming cluster nodes can pull without credentials.

GitHub packages default to private on first publish, so this visibility step is the one expected manual action before public cluster pulls work credential-free.

## Runner boundary

The AI activity runner remains a local/on-prem operator tool, not an EKS workload for the public demo. Keep runner credentials, bridge access, and runtime state outside Kubernetes manifests and public receipts. The GHCR workflow publishes only deployable app images (`backend` and `frontend`); run the runner from the on-prem environment against the public read/API boundary only after app health and mutation protection are verified.
