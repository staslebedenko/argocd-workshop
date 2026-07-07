# Step 5. ApplicationSet and Workshop Wrap-up

- **Hands-on:** Replace 3 near-identical Application manifests (common, frontend, backend) with a single `ApplicationSet`.
- Understand what an `ApplicationSet` actually is (a generator that stamps out Application manifests) and where it does/doesn't show up in the UI.
- Step back and look at where `ApplicationSet` fits among the other automation options we've used across this workshop.

## Application Set

First we need to switch root in the command line from the previous step to the step 5 infrastructure repo (all paths and apply commands below assume this folder):

```bash
cd ..
cd ..
cd 05_ApplicationSet_Summary/infrastructure-repo
```

Then we need to delete existing apps in Argo CD

```bash
kubectl delete application app-of-apps -n argocd  
kubectl delete application common-resources -n argocd  
kubectl delete application frontend-test -n argocd  
kubectl delete application backend-test -n argocd  
```

Note: `app-of-apps` carries the `resources-finalizer.argocd.argoproj.io` finalizer, so deleting it cascades and removes the three child Applications with it - the last three commands will usually just report `NotFound`. That is expected; they are there as a safety net in case your root app was created without the finalizer.

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

```bash
kubectl apply -f argo-cd-apps/application-set.yaml  
```

(Alternative: the CLI can create it too - `argocd appset create argo-cd-apps/application-set.yaml`.)

Since the ApplicationSet does not show up in the UI, the `argocd` CLI is your main window into it (requires the `argocd login` session from the earlier steps):

```bash
argocd appset list
argocd appset get dev-infra-appset
argocd app list
```

Optional: quick CLI cheat sheet for status + management:

```bash
# status
argocd appset list
argocd appset get dev-infra-appset

# manage
argocd appset create -f argo-cd-apps/application-set.yaml
argocd appset delete dev-infra-appset
```

`argocd appset get` is the first stop when a generator misbehaves: its output includes the **Conditions** (did parameter generation succeed, is there a template error) and the list of Applications it produced. Remember the community-feedback section below - a broken generator fails *silently* by producing no apps or the wrong apps, and this command is how you find out which.

The same information is available without an argocd login through plain kubectl - the conditions live in the resource status:

```bash
kubectl get applicationset -n argocd
kubectl describe applicationset dev-infra-appset -n argocd
```

A few things to note:

- The ApplicationSet itself is not visible in the UI - only the resulting Applications are. To inspect or remove it you go through kubectl or the CLI. The command below deletes the ApplicationSet **and cascades to all three generated Applications** - so don't run it now if you want to keep your deployment (it also requires an active `argocd login` session):

```bash
argocd appset delete dev-infra-appset
```

- We deliberately carried the `syncWave` values over from step 4 - but notice they change **nothing** here. Sync waves order resources within one parent Application's sync; Applications stamped out by an ApplicationSet are independent and each auto-syncs on its own, in parallel. Our deployment still works only because the `devbcn-demo` namespace already exists from step 4. Ordering across applications is an App-of-Apps feature, and that is one honest reason to pick it over an ApplicationSet when deployment order matters (see the comparison below).

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

- Do the hierarchical homework below (ApplicationSet -> App-of-Apps) - it ties together everything from steps 4 and 5.
- Try a `git` or `cluster` generator instead of the `list` generator we used, so new apps/environments show up automatically instead of being hand-listed.
- Split this single dev environment into multiple environments/clusters (see the "Complexity raises fast" note from step 3's summary).
- Explore Argo CD notifications and the structured JSON server logs we enabled in step 4 (the API server log is Argo CD's audit trail) for real alerting.

Want to replay the workshop on the same cluster? See [teardown.md](teardown.md) for how to safely remove Argo CD and all workshop deployments without re-provisioning AKS (deletion order matters because of Application finalizers).

Thanks for going through the whole workshop - now go build something and let Git argue with your cluster for you :)


## Homework: hierarchical setup - ApplicationSet on top, your step 4 App-of-Apps below

The two patterns compose. An `Application` CR is just a Kubernetes resource, so an ApplicationSet can generate *root* Applications - each one an App-of-Apps managing its own subtree. The generator decides **who gets a tree** (env, cluster, team); the App-of-Apps below decides **what is inside each tree, in what order** (sync waves work within a root's sync - something the flat ApplicationSet from this step cannot give you).

Let's put your existing step 4 App-of-Apps under an ApplicationSet.

### 1. Remove the flat ApplicationSet from this step

`dev-infra-appset` generates Applications named `common-resources`, `frontend-test` and `backend-test` - the same names your App-of-Apps children use. Two owners for the same Application means a prune/recreate fight, so the flat ApplicationSet has to go first (this cascades and removes its three generated apps):

```bash
kubectl delete applicationset dev-infra-appset -n argocd
```

### 2. Create the hierarchical ApplicationSet

New file in the infrastructure repository:

```yaml
# argo-cd-apps/root-appset.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: root-appset
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - env: dev
        path: step-4/argo-cd-apps/apps
  template:
    metadata:
      name: 'app-of-apps-{{env}}'
      namespace: argocd
      finalizers:
      - resources-finalizer.argocd.argoproj.io   # so deleting a root cascades to its children
    spec:
      project: common-resources                  # must allow the argocd namespace destination
      source:
        repoURL: https://github.com/staslebedenko/infrastructure-repo.git  # Change to your Repo URL
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: argocd                        # its resources are Application CRs
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

The template is your step 4 `app-of-apps.yaml`, parameterized. Apply it:

```bash
kubectl apply -f argo-cd-apps/root-appset.yaml
```

### 3. Verify the hierarchy

```bash
argocd appset get root-appset
kubectl get applications -n argocd
```

You should see `app-of-apps-dev` plus the three children it created (`common-resources`, `frontend-test`, `backend-test`) - a three-level chain: ApplicationSet (invisible in the UI) -> root app -> child apps -> workloads. The children roll out in wave order 0/1/2 because they are synced *by the root*, unlike in step 5's flat setup.

### 4. Think through scaling it (no need to execute)

Adding a second element (say `env: test` pointing at a `step-N/argo-cd-apps/apps-test` folder) would stamp out a second, complete tree. One rule keeps this safe: **the hierarchy must stay a tree, not a diamond** - each child Application folder (and each Application *name*) may be referenced by exactly one root. The child manifests in a second folder would need their own names (`frontend-test-test2` won't win prizes, `{{env}}`-suffixed names via a Helm-templated App-of-Apps would - see the middle-ground section above).

### 5. Cleanup - mind the triple cascade

Deleting `root-appset` now cascades **three levels**: the ApplicationSet deletes `app-of-apps-dev`, its finalizer cascades to the three children, and their finalizers prune the workloads. One command, empty namespace. That reach is exactly why production setups put `preserveResourcesOnDeletion: true` in the ApplicationSet's `syncPolicy` (or leave finalizers off the roots) as a circuit breaker:

```bash
kubectl delete applicationset root-appset -n argocd   # removes everything this homework created
```
