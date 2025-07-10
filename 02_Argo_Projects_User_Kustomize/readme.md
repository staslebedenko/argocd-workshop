# Step 2. Project, User and Kustomize overlays

1. Checking kubectl, kustomize, argo cli, az cli
2. Creating structure for infra repository
3. Connecting to our dev cluster
4. Restricting the default project
5. Adding new user
6. Adding new project
7. Adding access policy
8. Introduction to Kustomize concepts: bases, envs, patches.
9. Applying changes to cluster
10. To run commands here please switch to infra root, where you see subfolder argo-cd

### Pre-flight checks
Check 
```yaml
kustomize version
argocd version
kubectl get all -n argocd
```

if argo connection is not available, please run port forwarding below in powershell console
```yaml
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```

Also, you should do Argo login to cluster with cli from step 1

**Infrastructure repository structure**
```yaml
argo-cd/  
├── base/  
│   ├── install.yaml  
│   └── kustomization.yaml
└── envs/  
    └── dev/  
        ├── restrict-default-project.yaml  
        ├── argocd-cm-patch.yaml  
        ├── argocd-rbac-cm.yaml  
        ├── project-devbcn-demo.yaml  
        └── kustomization.yaml
```

### Setting up Argo base manifest

**install.yaml** - adding it from public agro url to base folder argo-cd/base
```yaml
https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

**kustomization.yaml** to the same folder argo-cd/base
```yaml
# argo-cd/base/kustomization.yaml  
resources:  
  - install.yaml  

namespace: argocd
```

### Creating folders for dev environment - envs/dev

And adding there 5 files below, they also just available in the folder

**kustomization.yaml** - sets they yaml structure for building manifests
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
```

**restrict-default-project.yaml** - to keep default project empty
```yaml
# argo-cd/envs/dev/restrict-default-project.yaml 
apiVersion: argoproj.io/v1alpha1  
kind: AppProject  
metadata:  
  name: default  
  namespace: argocd  
spec:  
  description: "Restricted default project - no access allowed"  
  sourceRepos: []  
  destinations: []  
  clusterResourceWhitelist: []  
  namespaceResourceWhitelist: []  
```

**argocd-cm-patch.yaml** - file that registers devbcn-user with Argo CD
```yaml
# argo-cd/envs/dev/argocd-cm-patch.yaml 
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: argocd-cm  
  namespace: argocd  
data:  
  accounts.devbcn-user: apiKey, login  
```

**argocd-rbac-cm-patch.yaml** - policy file to allow the new user access to the new project
```yaml
# argo-cd/envs/dev/argocd-rbac-cm-patch.yaml
apiVersion: v1  
kind: ConfigMap  
metadata:  
  name: argocd-rbac-cm  
  namespace: argocd  
data:  
  policy.csv: |  
    g, devbcn, role:devbcn-demo-admin  
  policy.default: role:readonly  
  scopes: '[groups]'  
policy.roles: |  
  # deny all global configuration actions  
  p, role:devbcn-demo-admin, *, *, *, deny  
  # allow full application access only within devbcn-demo project  
  p, role:devbcn-demo-admin, applications, *, devbcn-demo/*, allow  
  # allow read access to project details (recommended)  
  p, role:devbcn-demo-admin, projects, get, devbcn-demo, allow
```

**project-devbcn-demo.yaml**
```yaml
# argo-cd/envs/dev/project-devbcn-demo.yaml
apiVersion: argoproj.io/v1alpha1  
kind: AppProject  
metadata:  
  name: devbcn-demo  
  namespace: argocd  
spec:  
  description: "Project for devbcn deployments"  
  sourceRepos:  
    - "*" # Allow all repositories, or specify your Git repos explicitly  
  destinations:  
    - namespace: devbcn-demo # Allow all namespaces, or restrict to specific namespaces if needed  'https://your.git.repo/applications.git'
      server: "*"    # Allow all clusters, or restrict to specific clusters  
  clusterResourceWhitelist:  
    - group: "*"  
      kind: "*"  
  namespaceResourceWhitelist:  
    - group: "*"  
      kind: "*"  
```

Please double check that all changes in files are saved :), order of file creation is not important.

### Verifying that changes to Argo CD are correct and applying them to our Argo CD manually

* We covering application GitOps automation within the first 5 steps of workshop to keep time and complexity at check, but of course Argo CD updates should be automated in a GitOps way as well. 

First we will switch to the correct root folder in command line

```yaml
cd 02_Argo_Projects_User_Kustomize/infrastructure-repo
```

Execute command below to output Argo CD manifests with our updates(assuming you at root)
```yaml
kustomize build argo-cd\envs\dev\
```

Optional. To observe all change to Argo CD you can output result of combining install.yaml with all files referenced in Kustomize file to the new file result.yaml. Don’t forget to delete it afterwards from root folder.
```yaml
kustomize build argo-cd\envs\dev\ > result.yaml
```

If result manifest successfully outputed to console, we can apply all changes to our Kubernetes cluster
```yaml
kustomize build argo-cd\envs\dev\ | kubectl apply -f -  
```
![image](https://github.com/user-attachments/assets/b12abc1e-eab8-4a96-8c55-b09df288dd11)


To verify new project creation
```yaml
kubectl get appproject -n argocd devbcn-demo
```

(Optional) You can also deploy folders with kustomize overlays with kubectl, because kustomize is also part of kubectl
```yaml
kubectl apply -k argo-cd\envs\dev\ 
```

### New user setup
(Warning) Custom user management here strictly for education purposes, you should always use your EntraId accounts with custom access groups in Argo CD.

So, After creating the new user, we need to set a new password for it.

First we need to check if we are logged in with Argo cli
```yaml
argocd account get-user-info
```

Set user a new password for devbcn-demo user below, don’t forget to add your admin password below.

```yaml
argocd account update-password --server localhost:8080 --insecure --account devbcn-user --new-password password1234 --current-password supersecret:)
```
Login with your new user to Argo CD by entering new login: devbcn-user and password

You should see empty UI and have access to the new project devbcn-demo

### If you getting unauthorized error

It means that you need to login with admin account to Argo CD CLI and then return to setting password above

Start port forwarding to access our instance

```yaml
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```

Then update command below with your admin password and run it, --insecure used because of custom certificate.

```yaml
argocd login localhost:8080 --username admin --password supersecret:)  --insecure
```

Check access and current user

```yaml
argocd app list
argocd account get-user-info  
```

Set user a new password below, don’t forget to add your admin password below.

```yaml
argocd account update-password --server localhost:8080 --insecure --account devbcn-user --new-password password1234 --current-password supersecret:)
```

Login with your new user to Argo CD by entering new login: devbcn-user and password

You should see empty UI and have access to the new project devbcn-demo



### Infrastructure repository
Please add changes above to your public github repository, except for passwords :)

My repository for infrastructure, you can use it too
```yaml
https://github.com/staslebedenko/infrastructure-repo.git
```

This concludes part 2, and real fun begins :)
