# Step 3. Application deployment, templating, first issues

- **Hands-on:** Create a reusable base manifest for your application (deployment/service).
- **Hands-on:** Implement environment-specific envs for "test" and "prod":
    - Modify replica counts, resource limits, environment variables.
    - Inject environment-specific configuration (via ConfigMaps or Secret references).
- Deploy via Argo CD and verify environment-specific deployment.
- To run commands here please switch to infra root, where you see subfolder argo-cd

So far we have setup only Argo and its configuration structure, while working from a local machine, now is the time to work with applications, we will start with the single front-end app.

### Repository structure evolution

Now it is evolving to the following structure. 
```yaml
infrastructure-repo/  
├── apps/                                 # Kubernetes application manifests  
│   ├── common/  
│   │   ├── base/  
│   │   │   ├── namespace-devbcn.yaml     # Namespace definition for devbcn-demo  
│   │   │   └── kustomization.yaml  
│   │   └── envs/  
│   │       └── dev/  
│   │           └── kustomization.yaml    # Dev environment empty overlay  
│   │  
│   └── frontend/  
│       ├── base/  
│       │   ├── deployment.yaml           # Deployment frontend app  
│       │   ├── service.yaml              # Service frontend app  
│       │   └── kustomization.yaml  
│       └── envs/  
│           └── dev/  
│               ├── replicas-patch.yaml   # Replica count change for dev  
│               └── kustomization.yaml  
│  
├── argo-cd/                              # Argo CD installation and configuration manifests  
│   ├── base/  
│   │   ├── install.yaml                  # Base Argo CD installation manifest  
│   │   └── kustomization.yaml  
│   └── envs/  
│       └── dev/  
│           ├── argocd-cm-patch.yaml          # User creation devbcn-user  
│           ├── argocd-rbac-cm-patch.yaml     # RBAC for new project+user  
│           ├── kustomization.yaml  
│           ├── project-devbcn-demo.yaml      # Definition of Argo CD project for devbcn-demo  
│           └── restrict-default-project.yaml # Restrict default project access  
│  
└── argo-cd-apps/                        # Argo CD Application CRDs pointing to apps  
    ├── common/  
    │   └── base/  
    │       └── common-app.yaml          # manifest for common resources  
    └── frontend/  
        └── frontend-application.yaml    # manifest for frontend app  
```

### Applications
First we need to switch root in the command line from previous one

```yaml
cd ..
cd ..
cd 03_App_deployment_first_issues/infrastructure-repo
```

### Common folder

Base subfolder:
```yaml
# apps/common/base/namespace-devbcn.yaml 
apiVersion: v1  
kind: Namespace  
metadata:  
  name: devbcn-demo
```

**kustomization.yaml**
```yaml
# apps/common/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  
  
resources:  
  - namespace-devbcn.yaml 
```

Validate changes with command below, assuming that terminal is at root folder
```yaml
kustomize build apps/common/base/
```

* We ignoring dev specific overlay and leaving it empty for now, you can do this as part of home work

### Frontend app folder

Base subfolder:

```yaml
# apps/frontend/base/deployment.yaml
apiVersion: apps/v1  
kind: Deployment  
metadata:  
  name: frontend  
  namespace: devbcn-demo
spec:  
  replicas: 1  
  selector:  
    matchLabels:  
      app: frontend  
  template:  
    metadata:  
      labels:  
        app: frontend  
    spec:  
      containers:  
        - name: frontend  
          image: docker.io/stasiko/funneverends-frontend:latest  
          ports:  
            - containerPort: 80   
```

```yaml
# apps/frontend/base/service.yaml
apiVersion: v1  
kind: Service  
metadata:  
  name: frontend  
  namespace: devbcn-demo  
spec:  
  selector:  
    app: frontend  
  type: ClusterIP # Change to LoadBalancer if you need external exposure  
  ports:  
    - port: 80  
      targetPort: 80  
```

```yaml
# apps/frontend/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  
  
resources:  
  - deployment.yaml  
  - service.yaml  
```

### Dev overlays folder envs\dev

changed replicas count
```yaml
# apps/frontend/envs/dev/deployment-patch.yaml
apiVersion: apps/v1  
kind: Deployment  
metadata:  
  name: frontend  
  namespace: devbcn-demo 
spec:  
  replicas: 2  
```

```yaml
# apps/frontend/envs/dev/kustomization.yaml 
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  

resources:  
  - ../../base  

namespace: devbcn

patches:  
- path: deployment-patch.yaml 
```

Validate changes with 
```yaml
kustomize build apps/frontend/envs/dev/
```

(Sidenote)As you know, kustomize is a part of kubectl, so command below will also work. 
We separating them to make avoid mess

```yaml
kubectl kustomize apps/frontend/envs/dev/
```

## Argo CD application manifests (CRDs)

Argo CD Applications are special Kubernetes resources (called Custom Resources)

There will be simpler structure here, because Argo recommends less usage of Kustomize, because things can be messier this way :)

Now we are creating files in argo-cd-apps/common
```yaml
# argo-cd-apps/common/common-app.yaml 
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: common-resources  
  namespace: argocd  
  annotations:  
    argocd.argoproj.io/sync-wave: "0" 
spec:  
  project: common-resources  
  source:  
    repoURL: https://github.com/staslebedenko/infrastructure-repo.git  # Change to your Repo URL  
    targetRevision: HEAD  
    path: step-3\apps\common\base                # path to app manifest  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: default               # For namespaces use "default"
  syncPolicy:  
    automated:  
      prune: false                   # 
      selfHeal: true   
```

then argo-cd-apps/frontend

```yaml
# argo-cd-apps/frontend/frontend-application.yaml
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: frontend-test  
  namespace: argocd  
  annotations:  
    argocd.argoproj.io/sync-wave: "1" 
spec:  
  project: devbcn-demo  
  source:  
    repoURL: https://github.com/staslebedenko/dev-infrastructure.git  
    targetRevision: HEAD  
    path: step-3/apps/frontend/envs/dev  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: devbcn-demo
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true   
```

Argo CD sync waves allow you to orchestrate the deployment order of Kubernetes resources by adding annotations ([argocd.argoproj.io/sync-wave](http://argocd.argoproj.io/sync-wave)) to your manifests. Resources with lower sync-wave numbers (e.g., "0") are synchronized first, and only after they are successfully deployed does Argo CD proceed to resources with higher wave numbers (e.g., "1", "2", etc.). This helps manage dependencies clearly, ensuring critical resources—such as namespaces, CRDs, or other prerequisites—are deployed successfully before the applications or services relying on them begin deployment, thus providing safer and more controlled rollouts.

## Deployment fun

Now we will try to deploy our applications and fix some errors along the way.

First - please commit all files above to git repo and push it to your public github repo.  

Please do the switch context to your cluster, to avoid problems :)
```yaml
kubectl config use-context devbcn-cluster
kubectl get ns
```
You should have following namespace list as output
![image](https://github.com/user-attachments/assets/f452d615-cbf5-40f8-ae6d-d2c4d5688058)

Check if Argo is accessible via [localhost:8080](http://localhost:8080) - if not, restart port forwarding below
```yaml
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```

Then proceed with manual deployment of namespace and frontend app from the root. 
We will automate this during the next step of workshop with App of Apps pattern.

```yaml
kubectl apply -n argocd -f argo-cd-apps/common/common-app.yaml 
kubectl apply -n argocd -f argo-cd-apps/frontend/frontend-application.yaml
```

Now we have a following status, or something like this :)
![image](https://github.com/user-attachments/assets/faf739d2-83cb-45d5-9d90-6aadec0c3d28)


As you can see, deployment of common-resources app failed, but Argo showing it as healthy - why?

- Argo CD's "Health" status tracks the health of Kubernetes resources that **already exist**.
- If no Kubernetes resources are created yet (due to manifest-rendering errors), Argo CD has no resource statuses to report as unhealthy.
- Manifest-rendering issues (like missing paths or repository errors) affect **Sync Status**, not the Health Status.

### Error 1

Let’s start with the common-resources app. If we will try to open it - we will get informative error
![image](https://github.com/user-attachments/assets/f6756e11-db40-4584-8e67-12da3e5f273d)

And we cannot do anything from Argo CD UI, now is a good time to add new namespace to Argo CD
```yaml
# argo-cd/envs/dev/project-common-resources.yaml
apiVersion: argoproj.io/v1alpha1  
kind: AppProject  
metadata:  
  name: common-resources  
  namespace: argocd  
spec:  
  description: "Project for coomon deployments"  
  sourceRepos:  
    - "*" # Allow all repositories, or specify your Git repos explicitly  
  destinations:  
    - namespace: "*" # Allow all namespaces, or restrict to specific namespaces if needed  'https://your.git.repo/applications.git'
      server: "*"    # Allow all clusters, or restrict to specific clusters  
  clusterResourceWhitelist:  
    - group: "*"  
      kind: "*"  
  namespaceResourceWhitelist:  
    - group: "*"  
      kind: "*"  
```

And update kustomize to include this file

```yaml
# argo-cd/envs/dev/kustomization.yaml  
resources:  
  - ../../base  
  - restrict-default-project.yaml
  - project-devbcn-demo.yaml
  - project-common-resources.yaml
  
namespace: argocd  
  
patches:  
  - path: argocd-cm-patch.yaml  
  - path: argocd-rbac-cm-patch.yaml 
```

Test it
```yaml
kustomize build argo-cd\envs\dev\
```

And apply Argo CD changes

```yaml
kustomize build argo-cd\envs\dev\ | kubectl apply -f -
```

Let’s check status in UI :)And update kustomize to include this file
![image](https://github.com/user-attachments/assets/f43987d2-3769-4537-b21c-ea9c91852c6b)

### Error 2

Let’s open common-resources app 
(Important note, optional)If you getting Origin not allowed error, you just need to re-start port forwarding and login again

```yaml
taskkill /IM kubectl.exe /F
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```

![image](https://github.com/user-attachments/assets/1fb932cd-83e2-4dfa-bb7f-5465e71313d4)

![image](https://github.com/user-attachments/assets/9508d81e-6c86-463b-995c-761dc85e1a16)

Now we know that path inside manifest is wrong, lets fix it in UI.
Click DETAILS, MANIFEST, EDIT

![image](https://github.com/user-attachments/assets/364a642b-2361-475e-8b02-200938526804)

And change  step-3\apps\common\base to  step-3/apps/common/base
Click SAVE and click to EVENTS to see that Sync operation succeeded. 

If you will check with command below, you will see that new namespace is available

```yaml
kubectl get namespaces
```

! But that is not the end of this story, if you will check your github repository, it still contains manifest with error above, Argo CD don’t merge back changes done in the UI and it is a classic configuration drift after ClickOps activity. Next time you deploy or Argo sync this Common resources CRD manifest application will be broken again. Never ever do anything in the UI :).

### Error 3

Lets have a look at Frontend. With waves approach sync should not be started, or is it?

- If Wave `0` manifests **fail to render** (due to incorrect paths or invalid manifests), Argo CD will NOT create those resources at all, and the sync will show a `ComparisonError`.
- Because Wave `0` resources are never successfully synced (not created), Argo CD will **not proceed** to deploy Wave `1`.However, if Wave `0` has no resources at all (for example, due to a manifest rendering issue, Argo CD sees nothing to deploy), it may skip directly to Wave `1`. This can be confusing.
- If Wave `0` is empty (no resources created at all due to manifest errors), Argo CD treat that wave as trivially complete and proceed to Wave `1`.
- If Wave `0` has resources defined but fails due to **Kubernetes errors at apply-time** (e.g., validation errors, admission controllers, etc.), Argo CD stops and won't proceed to the next waves.

![image](https://github.com/user-attachments/assets/00ed35af-07f3-44f9-ae2f-295ff868a8d8)

Sync executing, but nothing happening
![image](https://github.com/user-attachments/assets/03b1755c-5003-4b59-aa09-984a79ee49b0)

Let’s open service
![image](https://github.com/user-attachments/assets/ba945ecf-a000-4fc6-a03d-87c4dab972a6)

And then Diff
![image](https://github.com/user-attachments/assets/5c6ec38f-45fb-4e7a-99f5-4f2ac42aa430)

We can deduct from this, that there are namespace mismatch, but error will not really providing useful information, lets fix it in Kustomize file in infrastructure repo.

Let’s fix namespace configuration in the dev overlay from devbcn to devbcn-demo, commit and push to repository

```yaml
# apps/frontend/envs/dev/kustomization.yaml 
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  

resources:  
  - ../../base  

namespace: devbcn-demo

patches:  
- path: deployment-patch.yaml 
```

Test it for correct namespace result
```yaml
kustomize build apps\frontend\envs\dev
```

!!! Important !!!
Change this kustomize file both in workshop repo and your infrastructure-repo, save commit and push to remote !

Frontend app is monitored by Argo CD from public remote repository infrastructure-repo.


We need to click SYNC and then SYNCHRONIZE
![image](https://github.com/user-attachments/assets/a63596ee-7742-46e1-a736-51100fcfb903)

![image.png](attachment:44c5ca0a-c2bd-426c-9828-cfe80ac589ea:image.png)

Quick explanation of the UI

- **PRUNE**: Delete Kubernetes resources not defined in Git manifests.
- **DRY RUN**: Preview sync without applying changes.
- **APPLY ONLY**: Apply manifests without waiting for resource readiness.
- **FORCE**: Recreate resources forcibly if normal apply fails (destructive).
- **SKIP SCHEMA VALIDATION**: Skip validation of manifests against Kubernetes schemas.
- **AUTO-CREATE NAMESPACE**: Automatically create missing namespaces during sync.
- **PRUNE LAST**: Delete resources after successful deployment of new resources.
- **APPLY OUT OF SYNC ONLY**: Apply only resources that differ from Git.
- **RESPECT IGNORE DIFFERENCES**: Respect rules defined for ignoring certain manifest differences.
- **SERVER-SIDE APPLY**: Use Kubernetes Server-Side Apply feature.
- **REPLACE**: Use 'kubectl replace' instead of 'kubectl apply' (destructive, careful!).
- **RETRY**: Automatically retry sync if it fails initially.
- **PRUNE PROPAGATION POLICY**: Controls how dependent resources are deleted (foreground/background).

And now everything is green
![image](https://github.com/user-attachments/assets/88868220-3414-4c2d-a024-adceaff6dad9)

(Optional) Synchronize options

## Exercises

### Failing of Frontend app sync - reverse change of namespace

Lets edit kustomize.yaml and revert namespace row set to devbcn, we already had our app green

```yaml
# apps/frontend/envs/dev/kustomization.yaml 
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  

namespace: devbcn

resources:  
  - ../../base  
  
patches:  
- path: deployment-patch.yaml 
```

Test if result manifest change to the new namespace with

```yaml
kustomize build apps/frontend/envs/dev/
```
And commit back to our repository, to see that we now have a Sync failed
![image](https://github.com/user-attachments/assets/e1aaa20b-f3ab-4593-a926-5ba2dfcacdbf)

In theory, sync with enabled Auto-create namespace should solve the problem, but this will not help in our situation, even with more destructive sync options enabled
![image](https://github.com/user-attachments/assets/51492828-e59a-48b2-be6d-d6d35f1c7217)

Another good thing that Argo keeping our app alive
![image](https://github.com/user-attachments/assets/e468efde-5bdf-452c-abcb-f816486ffb7a)

Whatever we will try to change in the sync, it will not help :)

## Auto healing

We will reverting changes of devbcnnamespace and ensuring that frontend application is green

Open ArgoCD UI, select Frontend, click DETAILS ⇒ SUMMARY ⇒ EDIT = SYNC POLICY and click on to the SELF HEAL - ENABLE. You will see button DISABLE after change.

Then we will delete our Frontend service with kubectl command

```yaml
kubectl -n devbcn-demo delete deployment frontend
```

This will result in out of sync, and then auto repair will happen. You might not even catch that this happen in UI
![image](https://github.com/user-attachments/assets/91520c74-7081-4b2e-ba0b-6b87e480634d)

And after a minute or two this would be reflected as a log entry

![image](https://github.com/user-attachments/assets/6a325cdc-c855-4c5d-a616-0bdf28f9bc2d)

In a few minutes it would be fixed.

### Summary

Please delete apps from ARGO UI before we proceed to the next step.

Lesson 1. Be consistent with structure, our allocation of base folder for deploying existing resource is a bad idea :)

Lesson 2. Complexity raises fast, be aware that we are working now still with one environment and single cluster.

- One Argo, one cluster - environments by namespaces
- One Argo, one cluster setup + 3 env clusters
- Argo per env, each env 2 clusters
- etc




