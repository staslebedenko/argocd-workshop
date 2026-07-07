# Cluster teardown - remove Argo CD and workshop deployments

Use this if you want to re-run the workshop flow on the same cluster without re-provisioning AKS.

The critical rule: **delete Argo CD's Applications while the Argo controller is still running**. The `resources-finalizer.argocd.argoproj.io` on them is processed by the controller - if you delete the `argocd` namespace first, Applications hang in deletion forever and the namespace gets stuck in `Terminating`.

## 1. Delete the ApplicationSet first

Otherwise it instantly recreates any Application you delete:

```bash
kubectl delete applicationset dev-infra-appset -n argocd --ignore-not-found
```

## 2. Delete all Applications and let the cascade finish

With the controller alive, the finalizers cascade-delete everything the apps deployed (frontend, backend, common resources):

```bash
kubectl delete applications --all -n argocd
kubectl get applications -n argocd    # wait until empty
```

If one hangs for more than a minute or two, strip its finalizer and delete again:

```bash
kubectl patch app <name> -n argocd -p '{"metadata":{"finalizers":null}}' --type merge
```

## 3. Delete the workshop namespace

Cleans anything the cascade missed - secrets, configmaps from the manual step-1 deployment:

```bash
kubectl delete namespace devbcn-demo --ignore-not-found
```

## 4. Delete the Argo CD namespace

Removes the install, projects, ConfigMaps and the initial admin secret:

```bash
kubectl delete namespace argocd
```

## 5. Delete the cluster-scoped leftovers

Namespace deletion does **not** remove these, and they are what makes a re-install behave oddly. Everything from the stable install carries the `part-of=argocd` label:

```bash
kubectl delete crd -l app.kubernetes.io/part-of=argocd
kubectl delete clusterrole,clusterrolebinding -l app.kubernetes.io/part-of=argocd
```

## 6. Only if you did the optional Azure Monitor part of step 4

The ServiceMonitors live outside the deleted namespaces:

```bash
kubectl get servicemonitors -A        # look for azmon-argocd-*
kubectl delete servicemonitor azmon-argocd-metrics azmon-argocd-repo-server-metrics azmon-argocd-server-metrics -n <namespace-shown> --ignore-not-found
```

The AKS managed-Prometheus addon itself is harmless to leave enabled.

## 7. Verify clean, then reset local state

```bash
kubectl get ns                                  # no argocd, no devbcn-demo
kubectl get crd | grep argoproj                 # nothing
kubectl get clusterrole | grep argocd           # nothing
argocd logout localhost:8080
```

On Windows also kill any old port-forwards:

```powershell
taskkill /IM kubectl.exe /F
```

After that the workshop replays cleanly from step 1's Argo CD install. A fresh `argocd-initial-admin-secret` is generated with a **new admin password** - don't reuse the recorded one.

Note: on re-install the Argo CD CRDs must be created from scratch, so `kubectl apply` **must** run with `--server-side` (as the step readmes show). Without it, the ~1MB ApplicationSet CRD overflows the 256KiB `last-applied-configuration` annotation and fails with `metadata.annotations: Too long`. If you mixed in a client-side apply first, run the next server-side apply once with `--force-conflicts`.

## If a namespace gets stuck in Terminating

The usual cause is an Application whose finalizer was never processed because the controller died first. Strip the finalizers from all remaining Applications:

PowerShell:

```powershell
kubectl get applications -n argocd -o name | % { kubectl patch $_ -n argocd -p '{\"metadata\":{\"finalizers\":null}}' --type merge }
```

bash:

```bash
kubectl get applications -n argocd -o name | xargs -I{} kubectl patch {} -n argocd -p '{"metadata":{"finalizers":null}}' --type merge
```

That releases the namespace within seconds - you should never need to touch the CRDs' own finalizers or restart the cluster.
