## Running containers locally, if you need to change code

All commands in this readme assume your terminal is in the `01_Intro_Apps_K8s_Tools_Argo/applications/` folder - the folder containing this readme, the docker-compose file and the k8s manifests.

If you need to test applications locally please use following commands (the second one tears everything down when you are finished)

```bash
docker-compose up --build
docker-compose down
```

Navigate to [http://localhost:8080](http://localhost:8080/) to access frontend app, no https :)

Redis from docker compose is published on host port **6380** (`localhost:6380`), so it does not clash with anything local. The port-forward command below is only for the **cluster** Redis, after you have done the manual deployment described later in this readme:

```bash
kubectl port-forward svc/redis -n devbcn-demo 6379:6379
```

## Authenticate with Docker Hub

You only need this if you plan to build and push your own images (next section). Pushing requires a [Docker Hub](https://hub.docker.com/) account - the free tier is enough.

Docker Hub recommends logging in with a **personal access token** instead of your account password (mandatory if your account uses two-factor authentication):

1. Sign in at [hub.docker.com](https://hub.docker.com/), go to **Account Settings -> Personal access tokens** ([direct link](https://app.docker.com/settings/personal-access-tokens)).
2. **Generate new token**, give it a name like `argocd-workshop` and **Read & Write** permissions, and copy the token - it is shown only once.

Then log in from the terminal (works the same in PowerShell and bash) - enter your Docker Hub username and paste the token when asked for the password:

```bash
docker login
```

You should see `Login Succeeded`. Docker Desktop on Windows stores the credentials in the system credential manager, so the login survives terminal restarts.

For non-interactive use (CI, scripts) pass the token via stdin instead, so it does not end up in your shell history:

```bash
echo <your-access-token> | docker login -u <your-dockerhub-user> --password-stdin
```

To end the session later:

```bash
docker logout
```

## Container preparation from repository
https://github.com/staslebedenko/DevBcn25-containers-without-Argo

Open a terminal on Windows, login to your docker registry (see the previous section), build two containers and push them to registry. Replace `<your-dockerhub-user>` with your own Docker Hub account - you cannot push to `stasiko/*` (the workshop's default images).

```bash
docker build -t <your-dockerhub-user>/funneverends-frontend:latest -f frontend/Dockerfile ./frontend
docker push <your-dockerhub-user>/funneverends-frontend:latest

docker build -t <your-dockerhub-user>/funneverends-backend:latest -f backend/Dockerfile ./backend
docker push <your-dockerhub-user>/funneverends-backend:latest
```

If you push your own images, remember to also update the `image:` fields in `backend-deployment.yaml` and `frontend-deployment.yaml` (they point to `docker.io/stasiko/...` by default), and later in the kustomize bases used from step 3 onwards.

## Login to Azure AKS access token and switch context to the current cluster

```bash
az login --use-device-code
az aks get-credentials --resource-group devbcn-demo --name devbcn-cluster --admin
kubectl config use-context devbcn-cluster-admin
```

## Please skip this step, this is needed only for the case when you are having issues with applications with your own changes.

```bash
kubectl apply -f namespace.yaml
kubectl apply -f backend-configmap.yaml
kubectl apply -f backend-secret.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f redis-deployment.yaml
```

Check deployed services with following commands

```bash
kubectl get configmaps,svc -n devbcn-demo
kubectl get svc frontend -n devbcn-demo
kubectl get svc backend -n devbcn-demo
```

if you need to delete namespace after manual deployment and testing

```bash
kubectl delete namespace devbcn-demo
```

if you need to rebuild container and redeploy your code

```bash
docker build -t stasiko/funneverends-frontend:latest -f frontend/Dockerfile ./frontend
docker push stasiko/funneverends-frontend:latest
kubectl rollout restart deployment/frontend -n devbcn-demo

docker build -t stasiko/funneverends-backend:latest -f backend/Dockerfile ./backend
docker push stasiko/funneverends-backend:latest
kubectl rollout restart deployment backend -n devbcn-demo

kubectl rollout status deployment backend -n devbcn-demo
kubectl describe deployment backend -n devbcn-demo
kubectl get pods -n devbcn-demo
```

To access and check if applications are working you need to start port forwarding. Each command blocks its terminal, so use three separate terminals (in bash you can instead append `&` to background them; the trailing `&` does not work in Windows PowerShell - there use `Start-Job -ScriptBlock { kubectl port-forward ... }`):

```bash
kubectl port-forward svc/backend -n devbcn-demo 5000:5000
kubectl port-forward svc/frontend -n devbcn-demo 8080:80
kubectl port-forward svc/redis -n devbcn-demo 6379:6379
```

Then access [http://localhost:8080](http://localhost:8080/) and check if your resources are working. 

And don't forget to stop these processes afterwards - on Windows the command below kills **all** kubectl processes (including the Argo CD port-forward from the main readme, restart it if you still need it):

```powershell
taskkill /IM kubectl.exe /F
```
