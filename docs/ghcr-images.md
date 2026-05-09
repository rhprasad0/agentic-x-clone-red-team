# GHCR image publishing

This repo publishes three container images to GitHub Container Registry (GHCR):

- `ghcr.io/rhprasad0/agentic-x-clone-red-team/backend`
- `ghcr.io/rhprasad0/agentic-x-clone-red-team/frontend`
- `ghcr.io/rhprasad0/agentic-x-clone-red-team/runner`

The workflow lives at `.github/workflows/publish-ghcr-images.yml` and runs on pushes to `main`, version tags matching `v*`, and manual `workflow_dispatch` runs.

## Permissions and secrets posture

The workflow uses only the repository-provided `GITHUB_TOKEN`:

- `contents: read` to check out the repo
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

## Runner image boundary

The `runner` image packages only `scripts/ai_activity_runner.py`, `scripts/fake_openai_compatible_llm.py`, and `scripts/ai_activity_runner_lib/`. It defaults to CLI help so a bare container run does not require private bridge credentials. Run it as a private Kubernetes Job or CronJob with bounded environment variables and private runtime state. It is not a public write surface.
