# Kubernetes manifests (reference architecture)

These are provided to demonstrate how this service would be deployed
to a Kubernetes cluster in production -- they are **not** currently
running on a live cluster. The live demo instead runs via a local
process behind a tunnel, for the reasons explained in the main
README ("Why the demo is a tunnel, not a cloud deployment") -- every
free-tier option for persistent hosting, Kubernetes included, requires
a paid account in the current (2026) landscape.

## What's here

- `deployment.yaml` -- a single-replica Deployment running the
  `parcelpilot-ai-support` image, pulling `GROQ_API_KEY` from a
  Kubernetes Secret rather than baking it into the image.
- `service.yaml` -- a NodePort Service exposing port 8000.

## To actually run this on a cluster

```bash
docker build -t parcelpilot-ai-support:latest .
kubectl create secret generic parcelpilot-secrets \
  --from-literal=GROQ_API_KEY=your_key_here
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

For a real production deployment, replace `imagePullPolicy: Never`
(which assumes a local image, e.g. via `minikube` or `kind`) with a
proper image pushed to a registry, and increase `replicas` behind a
load balancer -- the app's in-memory session storage would need to
move to Redis first, since sessions aren't currently shared across
replicas (see the README's "Design decisions" section).
