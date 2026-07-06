# Step 5. ApplicationSet and Workshop Wrap-up

- **Hands-on:** Replace 3 near-identical Application manifests (common, frontend, backend) with a single `ApplicationSet`.
- Understand what an `ApplicationSet` actually is (a generator that stamps out Application manifests) and where it does/doesn't show up in the UI.
- Step back and look at where `ApplicationSet` fits among the other automation options we've used across this workshop.

## Application Set

First we need to delete existing apps in Argo CD

```yaml
kubectl delete application app-of-apps -n argocd  
kubectl delete application common-resources -n argocd  
kubectl delete application frontend-test -n argocd  
kubectl delete application backend-test -n argocd  
```

Create a new application set file at `argo-cd-apps/application-set.yaml` in the infrastructure repository. Change the three `repoURL` values to your own repositories. Note that the common-resources path intentionally stays `step-4/apps/common/base` - we reuse the manifests pushed there in the previous step, nothing new is pushed in this one.

```yaml
apiVersion: argoproj.io/v1alpha1  
kind: ApplicationSet  
metadata:  
  name: dev-infra-appset  
  namespace: argocd  
spec:  
  generators:  
  - list:  
      elements:  
      - name: common-resources  
        repoURL: https://github.com/staslebedenko/infrastructure-repo.git  # Change to your Repo URL
        path: step-4/apps/common/base  
        namespace: default  
        project: common-resources  
        syncWave: "0"  
      - name: frontend-test  
        repoURL: https://github.com/staslebedenko/application-repo.git  # Change to your Repo URL
        path: infra/frontend/envs/dev  
        namespace: devbcn-demo  
        project: devbcn-demo  
        syncWave: "1"  
      - name: backend-test  
        repoURL: https://github.com/staslebedenko/application-repo.git  # Change to your Repo URL
        path: infra/backend/envs/dev  
        namespace: devbcn-demo  
        project: devbcn-demo  
        syncWave: "2"  
  template:  
    metadata:  
      name: '{{name}}'  
      namespace: argocd  
      annotations:  
        argocd.argoproj.io/sync-wave: '{{syncWave}}'  
    spec:  
      project: '{{project}}'  
      source:  
        repoURL: '{{repoURL}}'  
        targetRevision: HEAD  
        path: '{{path}}'  
      destination:  
        server: https://kubernetes.default.svc  
        namespace: '{{namespace}}'  
      syncPolicy:  
        automated:  
          prune: true  
          selfHeal: true  
```

and then apply 

```yaml
kubectl apply -f argo-cd-apps/application-set.yaml  
```

A few things to note, your application set is not visible in UI, only result applications

```yaml
argocd appset delete dev-infra-appset
```

## Which pattern should you actually use?

Across this workshop we've now used three different ways of getting manifests onto a cluster: plain `kubectl apply`, App-of-Apps (step 4), and `ApplicationSet` (this step). None of them is "the winner" - they trade off differently:

- **CLI/API based automation** (scripts calling `kubectl`/`argocd`/Terraform, etc.)
  - Very flexible, powered by a real programming language, supports any edge case.
  - Great troubleshooting toolset (it's just code).
  - Unfortunately requires real engineering effort to build and maintain.
- **App of Apps**
  - Very simple and fully declarative.
  - Does not require troubleshooting logic - if a child Application is wrong, you fix that one manifest.
  - Does not provide the best end-user experience once you have many near-identical apps (copy-pasted manifests, easy to drift).
- **ApplicationSet**
  - Fully declarative, and removes the copy-paste problem via generators (`list`, `git`, `cluster`, `matrix`, `merge`, ...).
  - Supports ~80% of use cases without much extra work (exactly what we did above).
  - Will require real work to support the remaining ~20% - generator logic (especially `matrix`/`merge`) gets complex fast.

### Real life ApplicationSet - community feedback

Worth knowing before you reach for `ApplicationSet` on a real platform: the community's experience with complex, production-grade ApplicationSets is decidedly mixed.

- A real ApplicationSet with multiple combined generators is effectively a small program - and it's a **hard program to troubleshoot**:
  - Lack of visibility into why a generator produced (or didn't produce) a given app.
  - Long retry/reconcile cycles make iterating on generator logic slow.
- Any mistake affects **all** apps the generator produces at once - unlike App-of-Apps where a broken child manifest only breaks that one app.
- It's genuinely difficult to get the generator logic right:
  - Misconfigured generators can produce **no apps at all**.
  - Or worse, silently produce the **wrong set of apps**.

For reference, here's what a real-world, production-grade generator setup looks like once you start combining `merge` and `matrix` generators (from a KubeCon talk on scaling ApplicationSets) - useful to know this exists, not something you need to memorize:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
spec:
  generators:
  - merge:
      mergeKeys:
        - metadata.labels.env
        - path.basename
      generators:
      - matrix:
          generators:
          - clusters: {}
          - git:
              repoURL: &repo https://github.com/alexmt/kubecon-2024-us.git
              directories:
              - path: clusters/base/*
      - merge:
          mergeKeys:
            - path
          generators:
          - git:
              repoURL: *repo
              revision: HEAD
              files:
              - path: clusters/groups/*/.env.yaml
          - git:
              repoURL: *repo
              revision: HEAD
              directories:
              - path: clusters/groups/*/*
```

### A middle ground worth knowing: App of Apps + Helm templating

Another pattern you'll see in the wild is a Helm-templated App-of-Apps - a `templates/application.yaml` that loops over a `values.yaml` list to stamp out one Application per entry:

```yaml
# templates/application.yaml
{{- range $i, $value := .Values.apps }}
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-service-{{ $value.name }}
spec:
  project: my-service
  source:
    repoURL: https://github.com/my-org/my-service.git
    targetRevision: HEAD
    path: {{ $value.name }}
  destination:
    name: qa-cluster
    namespace: my-service-{{ $value.name }}
{{- end }}
```
```yaml
# values.yaml
apps:
  - name: qa
  - name: stage
  - name: prod
```

It's Git-based and fully declarative, same as `ApplicationSet` - but it's **not** fully automated: adding a new environment still means manually editing `values.yaml`, unlike a `git`/`cluster` generator that can pick up new entries on its own. Good middle ground if your team already knows Helm and wants to avoid `ApplicationSet`'s generator complexity for a small, stable set of environments.

## Workshop Wrap-up

Looking back at the full journey:

- **Step 1** - got Argo CD running on AKS, manually, no Git involved yet.
- **Step 2** - locked down the default project, added a scoped project + user, and introduced Kustomize base/overlay structure.
- **Step 3** - deployed a real app through Argo CD Applications and debugged real sync errors (bad paths, missing projects, namespace drift, sync-wave surprises).
- **Step 4** - split infra/app repos for real, and replaced manual `kubectl apply` with the App-of-Apps pattern plus basic observability.
- **Step 5** (here) - replaced repetitive Application manifests with `ApplicationSet`, and looked at where it fits (and where it hurts) compared to the alternatives.

That's the whole GitOps loop: cluster -> Argo CD -> Git as the single source of truth -> automated, self-healing sync. From here, good next steps (homework) are:

- Try a `git` or `cluster` generator instead of the `list` generator we used, so new apps/environments show up automatically instead of being hand-listed.
- Split this single dev environment into multiple environments/clusters (see the "Complexity raises fast" note from step 3's summary).
- Explore Argo CD notifications and the audit log we enabled in step 4 for real alerting.

Thanks for going through the whole workshop - now go build something and let Git argue with your cluster for you :)
