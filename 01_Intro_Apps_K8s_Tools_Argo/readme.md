# Step 1. Introduction, Apps, Kubernetes and Argo CD

- Intro - what GitOps is and isn’t
- Workshop structure and goals
    - Try to do as much as possible during workshop and continue home, because content can be bigger than 2h
    - I will be going through workshop steps explaining them
- Practicalities
    - Application code, manifests, public registry
    - Checking if local tools are installed - docker, kubectl, kustomize ?
    - Connecting to Azure and AKS with --admin option
    - Installing Argo
    - Init of infra repository
    - Port forwarding on different command lines
    - Disabling Argo default project
    - Adding new user to Argo

## Applications
Applications prepared as two custom containers plus Redis instance, containers already deployed to public Docker registry and referenced in yaml manifests.
Plese do not deploy manifests with Kubectl, we will do this via Argo CD later.

I explained manifests and docker-compose setup at the end of this readmy, if case you will need it :).

## Argo CD setup

Login to Azure with device code from CMD
```yaml
az login --use-device-code
```

Deploy AKS cluster
```yaml
az group create --name devbcn-demo --location westeurope
az aks create --name devbcn-cluster --resource-group devbcn-demo --location westeurope --node-resource-group devbcn-demo-resources --enable-managed-identity --node-count 2 --generate-ssh-keys --enable-oidc-issuer --enable-workload-identity  
```

After cluster deployment we need to connect to it and add to local kube context

Login to Azure AKS access token and switch context to the current cluster
```yaml
az aks get-credentials --resource-group devbcn-demo --name devbcn-cluster --admin
kubectl config use-context devbcn-cluster
kubectl get all
```
* Please look at command line output for which name cluster is merged, you can use kubectl config get-contexts  to locate the correct context name

The next step would be setup default instance of Argo CD from public manifest 
```yaml
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl get all -n argocd
```

Next we need to output admin password for the instance we just deployed 

PS(Powershell) terminal (I'm using one in Visual Studio Code)
```yaml
$encodedPass = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"  
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedPass))  
```

(Optional)CMD terminal
```yaml
for /f %i in ('kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath^="{.data.password}"') do @powershell "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String(\"%i\"))"  
```

(Optional)Bash terminal
```yaml
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo  
```

Please record your password somewhere to use later, it looks something like below :)
C6#453$#532432E

Start background port forwarding and login to our Argo CD instance
```yaml
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```
Navigate to https://localhost:8080/ and login with login admin and password from console output above.

![image](https://github.com/user-attachments/assets/a1593750-6422-4a2d-9d22-fa498e4c3f4d)

It is also time to login with Argo CD CLI, this will be needed at the next step, replace password with your console output earlier

```yaml
argocd login localhost:8080 --username admin --password yourconsolepass  --insecure
argocd app list  
```

Step above might not work if your port forwarding is not active, if this is the case please restart it.


Alternative PowerShell terminal command for port-forwarding
```yaml
$job = Start-Job -ScriptBlock { kubectl port-forward svc/argocd-server -n argocd 8080:443 }
```
And killing of the process
```yaml
Stop-Job $job  
Remove-Job $job
```

Visit [https://localhost:8080](https://localhost:8080/)  Argo CD URL and login

Also make sure that you can login with Argo CD CLI, because this will be needed at the next step

```yaml
argocd logout localhost:8080 
argocd login localhost:8080 --username admin --password C6#453$#532432E  --insecure
argocd app list  
```

Repeating kubectl cleanup command
```yaml
taskkill /IM kubectl.exe /F
```

## Final notes

We approaching the main part of the workshop, please create new public github repositories

```yaml
infrastructure
application-repo
```

This concludes initial setup, please refer to readme in application folder for more details about application containers.

Remainder, if you need to stop working with port forwarding - just kill all processes, we need this active for the next steps, so keep console alive :)

```yaml
taskkill /IM kubectl.exe /F
```

Keep in mind that you can be connected to the wrong cluster/argo cd instance, if that would be the case double check active kubectl context, switch it to the correct one and logoff from ArgoCD

```yaml
kubectl config current-context
kubectl config get-contexts
kubectl config use-context <correct-context-name>  
argocd logout localhost:8080
```
