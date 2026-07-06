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
Please do not deploy manifests with Kubectl, we will do this via Argo CD later.

I explained manifests and docker-compose setup at the end of this readme, in case you need it :).

## Argo CD setup

Login to Azure with device code from CMD
```bash
az login --use-device-code
```

Deploy AKS cluster
```bash
az group create --name devbcn-demo --location westeurope
az aks create --name devbcn-cluster --resource-group devbcn-demo --location westeurope --node-resource-group devbcn-demo-resources --enable-managed-identity --node-count 2 --generate-ssh-keys --enable-oidc-issuer --enable-workload-identity  
```
* Do not pin `--node-vm-size` - leave it out and let Azure pick the default for your subscription. On some subscriptions the default VM size can come back as one that isn't allowed (e.g. `The VM size of Standard_D8a_v4 is not allowed in your subscription`). If that happens, just retry the same command again (Azure's default selection can vary between attempts), or list sizes allowed in your subscription/region and pass one explicitly with `--node-vm-size`:
```bash
az vm list-skus --location westeurope --resource-type virtualMachines --all --query "[?restrictions[0].reasonCode==null].name" -o table
```
* If a previous `az aks create` attempt failed partway (e.g. due to an invalid VM size) and a retry with the **same** cluster/resource group name gets stuck in `Creating` for a long time or ends up `Canceled`, don't keep waiting - delete both the resource group and its auto-generated node resource group (`<resource-group>-resources`), then retry with a fresh `az aks create`:
```bash
az group delete --name devbcn-demo --yes --no-wait
az group delete --name devbcn-demo-resources --yes --no-wait
```

After cluster deployment we need to connect to it and add to local kube context

Login to Azure AKS access token and switch context to the current cluster
```bash
az aks get-credentials --resource-group devbcn-demo --name devbcn-cluster --admin
kubectl config use-context devbcn-cluster-admin
kubectl get all
```
* The `--admin` flag merges the context as `<cluster-name>-admin` (e.g. `devbcn-cluster-admin`), not just `<cluster-name>` - use `kubectl config get-contexts` to double check the exact name if `use-context` fails.

The next step would be setup default instance of Argo CD from public manifest 
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl get all -n argocd
```

Next we need to output admin password for the instance we just deployed 

PS(Powershell) terminal (I'm using one in Visual Studio Code)
```powershell
$encodedPass = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"  
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedPass))  
```

(Optional)CMD terminal
```cmd
for /f %i in ('kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath^="{.data.password}"') do @powershell "[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String(\"%i\"))"  
```

(Optional)Bash terminal
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode; echo  
```

Please record your password somewhere to use later, it looks something like below :)
C6#453$#532432E

Start port forwarding and login to our Argo CD instance. The command occupies the terminal, so run it in a second terminal window and keep it running (in bash you can append `&` to background it; PowerShell does not support trailing `&` - use the `Start-Job` variant shown a bit below)
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Navigate to https://localhost:8080/ and login with login admin and password from console output above.

![image](https://github.com/user-attachments/assets/a1593750-6422-4a2d-9d22-fa498e4c3f4d)

It is also time to login with Argo CD CLI, this will be needed at the next step, replace password with your console output earlier

```bash
argocd login localhost:8080 --username admin --password yourconsolepass  --insecure
argocd app list  
```

Step above might not work if your port forwarding is not active, if this is the case please restart it.

* Note: any time you apply a change to Argo CD's own config (`argocd-cm`, `argocd-rbac-cm`, `argocd-cmd-params-cm`, etc. - this happens a lot from step 2 onwards), the `argocd-server` pod restarts to pick it up. Any running `kubectl port-forward` will die with `error: lost connection to pod` - just re-run the port-forward command. The `argocd` CLI may also show a one-time `server certificate had error ... Proceed insecurely (y/n)?` prompt afterwards (the pod's self-signed cert changed) - answer `y` and it won't ask again until the pod restarts again.


Alternative PowerShell terminal command for port-forwarding
```powershell
$job = Start-Job -ScriptBlock { kubectl port-forward svc/argocd-server -n argocd 8080:443 }
```
And killing of the process
```powershell
Stop-Job $job  
Remove-Job $job
```

Visit [https://localhost:8080](https://localhost:8080/)  Argo CD URL and login

Also make sure that you can login with Argo CD CLI, because this will be needed at the next step

```bash
argocd logout localhost:8080 
argocd login localhost:8080 --username admin --password "<your-password>" --insecure
argocd app list  
```
Keep the password quoted - initial Argo CD passwords often contain characters like `$`, `#` or `)` that PowerShell and bash otherwise interpret.

## Summary

By now you should have:
- A running AKS cluster with a default Argo CD instance installed from the public manifest.
- The admin password retrieved and a working login via both the UI and the `argocd` CLI.
- Sample containers (frontend/backend/redis) built and understood, but **not yet deployed** through Argo - that's the whole point of the next steps :)

Key takeaway: everything so far was done manually with `kubectl`/`az`/`argocd` CLI directly against the cluster - there is no Git repo driving any of this yet. Step 2 starts turning that around.

## Final notes

We approaching the main part of the workshop, please create new public github repositories

```text
infrastructure-repo
application-repo
```

This concludes initial setup, please refer to readme in application folder for more details about application containers.

Remainder, if you need to stop working with port forwarding - just kill all processes, we need this active for the next steps, so keep console alive :)

```powershell
taskkill /IM kubectl.exe /F
```

Keep in mind that you can be connected to the wrong cluster/argo cd instance, if that would be the case double check active kubectl context, switch it to the correct one and logoff from ArgoCD

```bash
kubectl config current-context
kubectl config get-contexts
kubectl config use-context <correct-context-name>  
argocd logout localhost:8080
```
