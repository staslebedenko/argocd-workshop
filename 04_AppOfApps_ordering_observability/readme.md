# ArgoCD 4. AppOfApps_ordering_observability

Repository with application code and app infra

```yaml
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

```yaml
root/  
├── apps/                                 # Kubernetes application manifests  
│   └── common/  
│       ├── base/  
│       │   ├── namespace-devbcn.yaml     # Namespace definition for devbcn-demo  
│       │   └── kustomization.yaml  
│       └── envs/  
│          └── dev/  
│              └── kustomization.yaml    # Dev environment empty overlay  
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
└── argo-cd-apps/                     # Argo CD Application CRDs pointing to apps  
			├── app-of-apps.yaml            # single Application pointing to apps folder  
			└── apps/  
			    ├── backend-app.yaml          
			    └── frontend-app.yaml         

```

Application manifests moving to the source code repository

```yaml
root/
├── backend   # source code of backend app
├── frontend  # source code of frontend app
├── infra/                                  
│   ├── backend/  
│   │   ├── base/
│   │   │   ├── deployment.yam  
│   │   │   ├── service.yaml       
│   │   │   └── kustomization.yaml  
│   │   └── envs/  
│   │       └── dev/
│   │           ├── replicas-patch.yaml   # Replica count change for dev  
│   │           └── kustomization.yaml    # Dev environment overlay can have new namespace  
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
```

A few steps here

- Move frontend app manifests to application repository
- Leave common manifest with Argo, since it is shared dependency
- Re-arrange argo-cd-apps by deleting existing apps from ArgoCD and deleting namespace bevbcn-demo

## Backend manifests introduction

First we need to switch root in the command line from previous one

```yaml
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
            - name: REDIS_CONN_STR  
              valueFrom:  
                secretKeyRef:  
                  name: backend-secret  
                  key: REDIS_CONN_STR  
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

And dev environment overlays for it at envs/dev

```yaml
# infra/envs/dev/backend-configmap-patch.yaml
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: backend-config  
  namespace: devbcn-demo  
data:  
  CORS_ALLOWED_ORIGIN: "http://localhost:8080"  
```

```yaml
# apps/backend/envs/dev/deployment-patch.yaml
apiVersion: apps/v1  
kind: Deployment 
metadata:  
  name: backend  
  namespace: devbcn-demo 
spec:  
  replicas: 2 
```

```yaml
# apps/backend/envs/dev/kustomization.yaml 
apiVersion: kustomize.config.k8s.io/v1beta1  
kind: Kustomization  

resources:  
  - ../../base  
  
patches:  
- path: deployment-patch.yaml
- path: backend-configmap-patch.yaml  
```

Before committing file, please double check them for errors with Kustomize build command, assuming you at the root folder of application repository, run commands below

```yaml
kustomize build infra/backend/envs/dev/
kustomize build infra/frontend/envs/dev/
```

You will get manifest output to the console after each commands

If everything looks cool, please commit and push all manifests to remote.
My repo url with source app code and manifests above is here.

```yaml
https://github.com/staslebedenko/application-repo
```

## Argo CD app of apps manifests

First we need to switch root in the command line from previous one

```yaml
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
spec:  
  project: devbcn-demo                 # or existing project name  
  source:  
    repoURL: https://github.com/staslebedenko/dev-infrastructure.git  
    targetRevision: HEAD  
    path: step-4/argo-cd-apps/apps        # child folder containing child manifests  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: argocd  
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true   
```

common-app.yaml 

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
    path: apps/common/base                # path to app manifest  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: default               # For namespaces use "default"
  syncPolicy:  
    automated:  
      prune: false                   # Be careful with pruning namespaces!  
      selfHeal: true  
```

frontend-application.yaml

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
    repoURL: https://github.com/staslebedenko/application-repo.git  
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

backend-application.yaml

```yaml
# argo-cd-apps/frontend/backend-application.yaml
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
    repoURL: https://github.com/staslebedenko/application-repo.git  
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
So no validation with Kustomize, but syntax validation with kubectl is possible with dry run option.

```yaml
kubectl apply --dry-run=client --validate=true -f argo-cd-apps/app-of-apps.yaml
```

## Deployment of App-of-Apps manifests

If everything is good, check again that you have the correct context with command below

```yaml
kubectl config current-context  
```

Now lets connect to our argo instance and delete all existing application there, just click on delete button of each application. Screenshot showing only one :)
![image](https://github.com/user-attachments/assets/32e40f5c-721a-45a4-9a18-715fa8a015a7)

Then we will double check what namespaces we have now

```yaml
kubectl get namespaces
```

If you get output like below, it means that devbcn-demo was deleted 

```yaml
NAME              STATUS   AGE
argocd            Active   11d
default           Active   11d
kube-node-lease   Active   11d
kube-public       Active   11d
kube-system       Active   11d
```

And now it is time for the one last kubectl apply our app of apps manifest

```yaml
kubectl apply -f argo-cd-apps/app-of-apps.yaml
```

Now we getting a new error with this deployment
![image](https://github.com/user-attachments/assets/5fd474de-a6f9-4cae-81d4-0c5c8c8ca8d4)

The root app of apps file should target namespace argo, but project devbcn-demo explicitly forbids any other namespaces, so we should change spec: project: devbcn-demo to common-resources to fix our problem

```yaml
# argo-cd-apps/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1  
kind: Application  
metadata:  
  name: app-of-apps  
  namespace: argocd  
spec:  
  project: common-resources                 # or existing project name  
  source:  
    repoURL: https://github.com/staslebedenko/dev-infrastructure.git  
    targetRevision: HEAD  
    path: step-4/argo-cd-apps/apps        # parent folder containing child manifests  
  destination:  
    server: https://kubernetes.default.svc  
    namespace: argocd    
  syncPolicy:  
    automated:  
      prune: true  
      selfHeal: true   
```

Apply manifest again and get 4 healthy applications

```yaml
kubectl apply -f argo-cd-apps/app-of-apps.yaml
```

![image](https://github.com/user-attachments/assets/3840b152-12be-4782-89d0-9942466db52c)

## Observability

Observability often a platform specific question, Azure, AWS, Splunk, DataDog, Dynatrace,

so we touch location command line wise and I will leave azure integration instruction 

We have 3 options here

- Kubectl
- Proper one :)

**Application deployment/sync issues logs:**

```yaml
kubectl logs -n argocd argocd-application-controller-0 --tail=10  
kubectl logs -n argocd deployment/argocd-repo-server --tail=10  
```

**User authentication/login logs:**

```yaml
kubectl logs -n argocd deployment/argocd-server --tail=10  
kubectl logs -n argocd deployment/argocd-dex-server --tail=10  
```

**Audit logs:**

```yaml
kubectl logs -n argocd deployment/argocd-server --tail=100 | Select-String audit | Select-Object -Last 10    
```

Audit by user, PS:

```yaml
kubectl logs -n argocd deployment/argocd-server | Select-String audit | Select-String admin  
```

The only problem we have here is that audit disabled :), double check if it is present, no result or false from command below means its is not

```yaml
kubectl get cm argocd-cm -n argocd -o jsonpath='{.data.server\.audit\.enabled}'  
```

* This is for homework :)

Please create a new patch for your argo instance

```yaml
# argo-cd/envs/dev/argocd-audit-log-patch.yaml
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: argocd-cm  
  namespace: argocd  
data:  
  server.audit.enabled: "true"  
  server.audit.logFormat: "json"  
```

Update kustomize file

```yaml
# argo-cd/envs/dev/kustomization.yaml  
resources:  
  - ../../base  
  - restrict-default-project.yaml
  - project-devbcn-demo.yaml
  
namespace: argocd  
  
patches:  
  - path: argocd-cm-patch.yaml  
  - path: argocd-rbac-cm-patch.yaml
  - path: argocd-audit-log-patch.yaml  
```

Test and apply changes with kustomize

```yaml
kustomize build argo-cd\envs\dev\
```

If all is ok, then go with 

```yaml
kustomize build argo-cd\envs\dev\ | kubectl apply -f -  
```

## (Optional)Observability with app insights

* This is optional part that can be done later on and depends on Azure

https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-argo-cd-integration

Code below is for azure bash console or local ps

```yaml
az extension add --name k8s-extension
### az aks update --enable-azure-monitor-metrics --name devbcn-demo1 --resource-group devbcn-demo1
### Use existing Azure Monitor workspace
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --azure-monitor-workspace-resource-id monitor-nrw

### Or Use an existing Azure Monitor workspace and link with an existing Grafana workspace
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --azure-monitor-workspace-resource-id monitor-nrw --grafana-resource-id  graphana-nrw

### Use optional parameters
az aks update --enable-azure-monitor-metrics --name devbcn-cluster --resource-group devbcn-demo --ksm-metric-labels-allow-list "namespaces=[k8s-label-1,k8s-label-n]" --ksm-metric-annotations-allow-list "pods=[k8s-annotation-1,k8s-annotation-n]"
```

To get default instance:  DefaultAzureMonitorWorkspace-westeurope

```yaml
az resource list --resource-type microsoft.monitor/accounts --query "[?contains(name,'DefaultAzureMonitorWorkspace')].{Name:name, ID:id}" -o table  
```

Appy cluster manifest

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

```yaml
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

Import official Graphana dashboard from Argo labs
https://grafana.com/grafana/dashboards/14584-argocd/

With command below 

```yaml
az grafana dashboard import --name argocd --resource-group igor-demo --definition 14584
```

## End


