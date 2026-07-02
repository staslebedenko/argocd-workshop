## Running containers locally, if you need to change code

If you need to test local applications please use following code, 

```yaml
docker-compose -f applications/docker-compose.yaml up --build
docker-compose -f applications/docker-compose.yaml down
docker-compose -f applications/docker-compose.yaml up --build
```

Navigate to [http://localhost:8080](http://localhost:8080/) to access frontend app, no https :)

If you need to work with Redis from your local docker compose, please execute all steps below and run command

```yaml
kubectl port-forward svc/redis -n devbcn-demo 6379:6379
```

## Container preparation from repository
https://github.com/staslebedenko/DevBcn25-containers-without-Argo

Open cmd shell on Windows, login to your docker registry, build two containers and push them to registry. Make sure you are in the root directory where the docker-compose file is located.

```yaml
docker login

docker build -t stasiko/funneverends-frontend:latest -f frontend/Dockerfile ./frontend
docker push stasiko/funneverends-frontend:latest

docker build -t stasiko/funneverends-backend:latest -f backend/Dockerfile ./backend
docker push stasiko/funneverends-backend:latest
```

## Login to Azure AKS access token and switch context to the current cluster

```yaml
az login --use-device-code
az aks get-credentials --resource-group devbcn-demo --name devbcn-cluster
kubectl config use-context devbcn-cluster
```

## Please skip this step, this is needed only for the case when you are having issues with applications with your own changes.

```yaml
kubectl apply -f applications/namespace.yaml
kubectl apply -f applications/backend-configmap.yaml
kubectl apply -f applications/backend-secret.yaml
kubectl apply -f applications/backend-deployment.yaml
kubectl apply -f applications/frontend-deployment.yaml
kubectl apply -f applications/redis-deployment.yaml
```

Check deployed services with following commands

```yaml
kubectl get configmaps,svc -n devbcn-demo
kubectl get svc frontend -n devbcn-demo
kubectl get svc backend -n devbcn-demo
```

if you need to delete namespace after manual deployment and testing

```yaml
kubectl delete namespace devbcn-demo
```

if you need to rebuild container and redeploy your code

```yaml
docker build -t stasiko/funneverends-frontend:latest ./frontend
docker push stasiko/funneverends-frontend:latest
kubectl rollout restart deployment/frontend -n devbcn-demo

docker build -t stasiko/funneverends-backend:latest -f backend/Dockerfile ./backend
docker push stasiko/funneverends-backend:latest
kubectl rollout restart deployment backend -n devbcn-demo

kubectl rollout status deployment backend -n devbcn-demo
kubectl describe deployment backend -n devbcn-demo
kubectl get pods -n devbcn-demo
```

To access and check if applications working you need to start port forwarding as background tasks

```yaml
kubectl port-forward svc/backend -n devbcn-demo 5000:5000 &
kubectl port-forward svc/frontend -n devbcn-demo 8080:80 &
kubectl port-forward svc/redis -n devbcn-demo 6379:6379 &
```

Then access [http://localhost:8080](http://localhost:8080/) and check if your resources are working. 

And don’t forget to kill these processes afterwards with

```yaml
taskkill /IM kubectl.exe /F
```
