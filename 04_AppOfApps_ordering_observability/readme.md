# Step 4. App of Apps, ordering and observability

Repository with application code and app infra

```text
https://github.com/staslebedenko/application-repo.git
https://github.com/staslebedenko/infrastructure-repo.git
```

## Plan

- Splitting repositories to Argo+Infrastructure and team repository with containers
- Preparing App of apps pattern manifest for existing applications.
- Adding new application to team repository (backend)
- Ordered deployment and issues
- Observability basics, avoiding ArgoCD user interface.

## App of Apps simplicity

You will need to split your infrastructure files into different repositories
Argo CD configs and Applications staying in the same repo

```text
root/  
├── apps/                                 # Kubernetes application manifests  
│   └── common/  
│       └── base/  
│           ├── namespace-devbcn.yaml     # Namespace definition for devbcn-demo  
│           └── kustomization.yaml  
│  
├── argo-cd/                              # Argo CD installation and configuration manifests  
│   ├── base/  
│   │   ├── install.yaml                  # Base Argo CD installation manifest  
│   │   └── kustomization.yaml  
│   └── envs/  
│       └── dev/  
│           ├── argocd-cm-patch.yaml          # User creation devbcn-user  
│           ├── argocd-rbac-cm-patch.yaml     # RBAC for new project+user  
│           ├── argocd-cmd-params-patch.yaml  # JSON logging (created in the observability section below)  
│           ├── kustomization.yaml  
│           ├── project-devbcn-demo.yaml      # Definition of Argo CD project for devbcn-demo  
│           ├── project-common-resources.yaml # Project for shared resources (created in step 3)  
│           └── restrict-default-project.yaml # Restrict default project access  
│  
└── argo-cd-apps/                     # Argo CD Application CRDs pointing to apps  
    ├── app-of-apps.yaml              # single Application pointing to apps folder  
    └── apps/  
        ├── backend-application.yaml          
        ├── frontend-application.yaml         
        └── common-app.yaml  
```

Application manifests moving to the source code repository

```text
root/
├── backend   # source code of backend app
├── frontend  # source code of frontend app
├── infra/                                  
│   ├── backend/  
│   │   ├── base/
│   │   │   ├── deployment.yaml  
│   │   │   ├── service.yaml       
│   │   │   ├── backend-configmap.yaml  
│   │   │   └── kustomization.yaml  
│   │   └── envs/  
│   │       └── dev/
│   │           ├── deployment-patch.yaml        # Replica count change for dev  
│   │           ├── backend-configmap-patch.yaml # Config override for dev  
│   │           ├── service-patch.yaml           # Service tweak for dev  
│   │           └── kustomization.yaml  
│   │  
│   └── frontend/  
│       ├── base/  
│       │   ├── deployment.yaml           # Deployment frontend app  
│       │   ├── service.yaml              # Service frontend app  
│       │   └── kustomization.yaml  
│       └── envs/  
│           └── dev/  
│               ├── deployment-patch.yaml   # Replica count change for dev  
│               └── kustomization.yaml  
```

A few steps here

- Move frontend app manifests to application repository
- Leave common manifest with Argo, since it is shared dependency
- Re-arrange argo-cd-apps by deleting existing apps from ArgoCD and deleting namespace devbcn-demo

## Backend manifests introduction

First we need to switch root in the command line from previous one

```bash
cd ..
cd ..
cd 04_AppOfApps_ordering_observability/application-repo
```

We have now our “beautiful” :) backend application, so lets deploy it 

```yaml
# infra/backend/base/backend-configmap.yaml
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: backend-config  
  namespace: devbcn-demo  
data:  
  CORS_ALLOWED_ORIGIN: "http://localhost:8080"  
```

```yaml
# infra/backend/base/deployment.yaml
apiVersion: apps/v1  
kind: Deployment  
metadata:  
  name: backend  
  namespace: devbcn-demo  
spec:  
  replicas: 1  
  selector:  
    matchLabels:  
      app: backend  
  template:  
    metadata:  
      labels:  
        app: backend  
    spec:  
      containers:  
        - name: backend  
          image: docker.io/stasiko/funneverends-backend:latest  
          ports:  
            - containerPort: 5000  
          env:  
            - name: CORS_ALLOWED_ORIGIN  
              valueFrom:  
                configMapKeyRef:  
                  name: backend-config  
                  key: CORS_ALLOWED_ORIGIN   
```

```yaml
# infra/backend/base/service.yaml
apiVersion: v1  
kind: Service  
metadata:  
  name: backend  
  namespace: devbcn-demo  
spec:  
  selector:  
    app: backend  
  ports:  
    - port: 5000  
      targetPort: 5000  
```

```yaml
# infra/backend/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  
  
resources:  
  - deployment.yaml  
  - service.yaml
  - backend-configmap.yaml   
```

And dev environment overlays for it at envs/dev. The ConfigMap patch carries the same CORS value as the base - for our single dev environment the patch exists to demonstrate the per-environment override mechanism (and to carry the wave annotation below); with a real test/prod split each env would set its own URL here. Note the `argocd.argoproj.io/sync-wave` annotations: these are **resource-level** waves - when Argo CD syncs the backend application, it applies the ConfigMap (wave 0) first, then the Service (wave 1), then the Deployment (wave 2), so the Deployment never starts before the config it mounts exists. This is the same wave mechanism we will use to order whole applications later in this step - waves order resources within one Application's sync.

```yaml
# infra/backend/envs/dev/backend-configmap-patch.yaml
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: backend-config  
  namespace: devbcn-demo
  annotations:  
    argocd.argoproj.io/sync-wave: "0"    
data:  
  CORS_ALLOWED_ORIGIN: "http://localhost:8080"  
```

```yaml
# infra/backend/envs/dev/service-patch.yaml
apiVersion: v1  
kind: Service  
metadata:  
  name: backend  
  namespace: devbcn-demo 
  annotations:  
    argocd.argoproj.io/sync-wave: "1"   
spec:  
  selector:  
    app: backend  
  ports:  
    - port: 5000  
      targetPort: 5000  
```

```yaml
# infra/backend/envs/dev/deployment-patch.yaml
apiVersion: apps/v1  
kind: Deployment 
metadata:  
  name: backend  
  namespace: devbcn-demo
  annotations:  
    argocd.argoproj.io/sync-wave: "2"   
spec:  
  replicas: 2 
```

```yaml
# infra/backend/envs/dev/kustomization.yaml 
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  

resources:  
  - ../../base  
  
patches:  
- path: deployment-patch.yaml
- path: backend-configmap-patch.yaml  
- path: service-patch.yaml
```

Before committing file, please double check them for errors with Kustomize build command, assuming you are at the root folder of application repository, run commands below

```bash
kustomize build infra/backend/envs/dev/
kustomize build infra/frontend/envs/dev/
```

You will get manifest output to the console after each commands

If everything looks cool, please commit and push all manifests to your public `application-repo` (this repo keeps its normal root layout - no step-N folders here, only the infrastructure repo uses them).
My repo url with source app code and manifests above is here, for reference:

```text
https://github.com/staslebedenko/application-repo
```

## Argo CD app of apps manifests

First we need to switch root in the command line from previous one

```bash
cd ..
cd infrastructure-repo
```

This single application points explicitly to your apps folder containing child manifests:

```yaml
# argo-cd-apps/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: app-of-apps  
  namespace: argocd  
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:  
  project: devbcn-demo                 # or existing project name  
  source:  
    repoURL: https://github.com/staslebedenko/infrastructure-repo.git  # Change to your Repo URL
    targetRevision: HEAD  
    path: step-4/argo-cd-apps/apps        # parent folder containing child manifests  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: argocd  
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true  
      allowEmpty: true
```

```yaml
# argo-cd-apps/apps/common-app.yaml 
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
    path: step-4/apps/common/base         # path to app manifest  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: default               # For namespaces use "default"
  syncPolicy:  
    automated:  
      prune: false                   # Be careful with pruning namespaces!  
      selfHeal: true  
```

```yaml
# argo-cd-apps/apps/frontend-application.yaml
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
    repoURL: https://github.com/staslebedenko/application-repo.git  # Change to your Repo URL
    targetRevision: HEAD  
    path: infra/frontend/envs/dev  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: devbcn-demo  
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true  
```

```yaml
# argo-cd-apps/apps/backend-application.yaml
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: backend-test  
  namespace: argocd  
  annotations:  
    argocd.argoproj.io/sync-wave: "2" 
spec:  
  project: devbcn-demo  
  source:  
    repoURL: https://github.com/staslebedenko/application-repo.git  # Change to your Repo URL
    targetRevision: HEAD  
    path: infra/backend/envs/dev  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: devbcn-demo  
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true  
```

First thing you can notice, that there is no Kustomize overlays for these manifests, as per Argo best practices, links below :). 
So no validation with Kustomize, but syntax validation with kubectl is possible with dry run option below.
```bash
kubectl apply --dry-run=client --validate=true -f argo-cd-apps/app-of-apps.yaml
```

Now commit and push these manifests to **your** infrastructure repository, into the `step-4/` folder (same step-N convention as before). The root app reads `step-4/argo-cd-apps/apps` from git, so Argo CD only sees the child applications after they are pushed. Double-check that `repoURL` in `app-of-apps.yaml` and in all three child manifests points to your repositories (infrastructure-repo for common, application-repo for frontend/backend).

## Deployment of App-of-Apps manifests

If everything is good, check again that you have the correct context with command below

```bash
kubectl config current-context  
```

Now lets connect to our argo instance and delete all existing application there, just click on delete button of each application. Screenshot showing only one :)
![image](https://github.com/user-attachments/assets/32e40f5c-721a-45a4-9a18-715fa8a015a7)

Then we will double check what namespaces we have now

```bash
kubectl get namespaces
```

If you get output like below, it means that devbcn-demo was deleted 

```text
NAME              STATUS   AGE
argocd            Active   11d
default           Active   11d
kube-node-lease   Active   11d
kube-public       Active   11d
kube-system       Active   11d
```

And now it is time for the one last kubectl apply our app of apps manifest

```bash
kubectl apply -f argo-cd-apps/app-of-apps.yaml
```

!!!Important thing!!! App of Apps manifest should target argocd namespace and argo project should allow this :), otherwise you can get error like below.
![image](https://github.com/user-attachments/assets/5fd474de-a6f9-4cae-81d4-0c5c8c8ca8d4)

The root app of apps file should always target destination namespace argocd, but if for example, our project devbcn-demo will explicitly forbid any other namespaces, then we should explicitly set this App of Apps manifest to  common-resources project.

```yaml
# argo-cd-apps/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: app-of-apps  
  namespace: argocd  
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:  
  project: common-resources                 # or existing project name  
  source:  
    repoURL: https://github.com/staslebedenko/infrastructure-repo.git  # Change to your Repo URL
    targetRevision: HEAD  
    path: step-4/argo-cd-apps/apps        # parent folder containing child manifests  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: argocd    
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true  
      allowEmpty: true
```

## Observability - optional step

Observability is often a platform specific question, Azure, AWS, Splunk, DataDog, Dynatrace,

so we touch location command line wise and I will leave azure integration instruction 

We have two options here

- Kubectl
- Proper one :)

**Application deployment/sync issues logs:**

```bash
kubectl logs -n argocd argocd-application-controller-0 --tail=10  
kubectl logs -n argocd deployment/argocd-repo-server --tail=10  
```

**User authentication/login logs:**

```bash
kubectl logs -n argocd deployment/argocd-server --tail=10  
kubectl logs -n argocd deployment/argocd-dex-server --tail=10  
```

**Audit trail:**

Argo CD has no separate audit-log switch - the API server log *is* the audit trail. Every user action (login, app create/delete, sync, rollback) arrives as an API call and gets logged by `argocd-server`. For example, to see the recent API activity (PowerShell):

```powershell
kubectl logs -n argocd deployment/argocd-server --tail=200 | Select-String "grpc.method" | Select-Object -Last 10
```

What we *can* improve is the format: by default these are plain-text lines, which are painful to filter or ship to a log platform. Argo CD components read their startup flags from the `argocd-cmd-params-cm` ConfigMap, and it supports structured JSON logging.

* This is for homework :)

Please create a new patch for your argo instance

```yaml
# argo-cd/envs/dev/argocd-cmd-params-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.format: "json"
  server.log.level: "info"
```

Update kustomize file

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
  - path: argocd-cmd-params-patch.yaml  
```

Test and apply changes with kustomize

```powershell
kustomize build argo-cd\envs\dev\
```

If all is ok, then go with 

```powershell
kustomize build argo-cd\envs\dev\ | kubectl apply -f -  
```

Verify the setting landed in the ConfigMap:

```bash
kubectl get cm argocd-cmd-params-cm -n argocd -o jsonpath="{.data.server\.log\.format}"
```

* Unlike `argocd-cm`, the `argocd-cmd-params-cm` values are read once at startup, so the server needs an explicit restart to pick them up (this will also drop your `kubectl port-forward` - restart it and re-login with the CLI if needed, see step 1's note):

```bash
kubectl rollout restart deployment argocd-server -n argocd
```

After the restart, the same log command returns JSON lines you can feed into any log platform:

```bash
kubectl logs -n argocd deployment/argocd-server --tail=5
```

## (Optional)Observability with app insights

* This is optional part that can be done later on and depends on Azure

https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-argo-cd-integration

Code below is for azure bash console or local ps

Both `--azure-monitor-workspace-resource-id` and `--grafana-resource-id` expect **full ARM resource IDs**, not workspace names - so first look up the ID of your Azure Monitor workspace (a default one like `DefaultAzureMonitorWorkspace-westeurope` usually already exists):

```bash
az resource list --resource-type microsoft.monitor/accounts --query "[?contains(name,'DefaultAzureMonitorWorkspace')].{Name:name, ID:id}" -o table  
```

And, if you want the Grafana link, the ID of your Azure Managed Grafana workspace:

```bash
az grafana list --query "[].{Name:name, ID:id}" -o table
```

Then enable managed Prometheus metrics on the cluster, pasting the IDs from above:

```bash
az extension add --name k8s-extension

### Use existing Azure Monitor workspace
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --azure-monitor-workspace-resource-id "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/microsoft.monitor/accounts/<workspace-name>"

### Or Use an existing Azure Monitor workspace and link with an existing Grafana workspace
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --azure-monitor-workspace-resource-id "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/microsoft.monitor/accounts/<workspace-name>" --grafana-resource-id "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Dashboard/grafana/<grafana-name>"

### Use optional parameters
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --ksm-metric-labels-allow-list "namespaces=[k8s-label-1,k8s-label-n]" --ksm-metric-annotations-allow-list "pods=[k8s-annotation-1,k8s-annotation-n]"
```

Apply cluster manifest

```yaml
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: azmon-argocd-metrics
spec:
  labelLimit: 63
  labelNameLengthLimit: 511
  labelValueLengthLimit: 1023
  selector:
    matchLabels:
     app.kubernetes.io/name: argocd-metrics
  namespaceSelector:
    any: true
  endpoints:
  - port: metrics
---
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: azmon-argocd-repo-server-metrics
spec:
  labelLimit: 63
  labelNameLengthLimit: 511
  labelValueLengthLimit: 1023
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-repo-server
  namespaceSelector:
    any: true
  endpoints:
  - port: metrics
---
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: azmon-argocd-server-metrics
spec:
  labelLimit: 63
  labelNameLengthLimit: 511
  labelValueLengthLimit: 1023
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-server-metrics
  namespaceSelector:
    any: true
  endpoints:
  - port: metrics
```

Assuming everything went without errors, then you can navigate to your Azure Monitor Workspace and use following queries to get logs

```kusto
ContainerLog  
| where Namespace == "argocd"  
| order by TimeGenerated desc  
| take 100  

ContainerLog  
| where Namespace == "argocd"  
| where LogEntry contains "error"  
| order by TimeGenerated desc  
| take 100  

KubeEvents  
| where Namespace == "argocd"  
| where ObjectKind in ("Application", "Deployment", "ReplicaSet", "Pod")  
| where Reason in ("ScalingReplicaSet", "SuccessfulCreate", "SuccessfulDelete", "Created", "Updated", "SyncSuccessful", "SyncFailed")  
| order by TimeGenerated desc  
| take 100  

```

Import official Grafana dashboard from Argo labs
https://grafana.com/grafana/dashboards/14584-argocd/

With command below - note that `--name` is the name of your **Grafana workspace**, not the dashboard:

```bash
az grafana dashboard import --name <your-grafana-workspace-name> --resource-group devbcn-demo --definition 14584
```

## Summary

Lesson 1. App-of-Apps turns "apply N Application manifests by hand" into "apply one root Application, let it manage the rest" - the root app just points at a folder of child Application manifests.

Lesson 2. Sync-wave ordering (`argocd.argoproj.io/sync-wave`) is cooperative, not a guarantee - if an earlier wave fails to render at all (bad path, bad repo), Argo CD may still consider it "done" and move on. Don't rely on waves alone for critical ordering; verify actual resource health too.

Lesson 3. The root App-of-Apps manifest's own `project` and `destination.namespace` matter - it needs a project that allows deploying into the `argocd` namespace itself, or you'll get a confusing rejection.

With backend + frontend + common resources all flowing through Git now, step 5 shows how to stop hand-writing near-identical Application manifests for each one.

## End


