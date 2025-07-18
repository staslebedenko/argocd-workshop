## Application Set

First we need to delete existing apps in Argo CD

```yaml
kubectl delete application app-of-apps -n argocd  
kubectl delete application common-resources -n argocd  
kubectl delete application frontend-test -n argocd  
kubectl delete application backend-test -n argocd  
```

Create a new application set file

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
        repoURL: https://github.com/staslebedenko/infrastructure-repo.git  
        path: step-4/apps/common/base  
        namespace: default  
        project: common-resources  
        syncWave: "0"  
      - name: frontend-test  
        repoURL: https://github.com/staslebedenko/application-repo.git  
        path: infra/frontend/envs/dev  
        namespace: devbcn-demo  
        project: devbcn-demo  
        syncWave: "1"  
      - name: backend-test  
        repoURL: https://github.com/staslebedenko/application-repo.git  
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
kubectl apply -f application-set.yaml  
```

A few things to note, your application set is not visible in UI, only result applications

```yaml
argocd appset delete dev-infra-appset
```
