## GitOps via Argo CD on Azure

### Requirements
* Provisioned Kubernetes cluster on any cloud
* Command line tools Kubectl, Kustomize, Argo CD CLI
* Optional Azure CLI if you are working with Azure Kubernetes Service AKS

- **kubectl** ([Installation instructions](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/))
- **Git for Windows** ([Installation instructions](https://git-scm.com/download/win))
- **Argo CD CLI** (`argocd`) ([Installation instructions](https://argo-cd.readthedocs.io/en/stable/cli_installation/#windows))
- **Kustomize CLI** ([Installation instructions](https://kubectl.docs.kubernetes.io/installation/kustomize/binaries/#windows))
- **Azure CLI** ([Installation instructions](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?view=azure-cli-latest&pivots=winget)) 
Kustomize is also a part of kubectl :)

Alternatively use following winget commands
winget install -e --id Kubernetes.kubectl
winget install -e --id Git.Git
winget install -e --id argoproj.argocd
winget install -e --id Kubernetes.kustomize
winget install --exact --id Microsoft.AzureCLI

### Instructions
Each step of workshop contains own readme with detailed flow plus complete code.

* 01_Intro_Apps_K8s_Tools_Argo
* 02_Argo_Projects_User_Kustomize
* 03_App_deployment_first_issues
* 04_AppOfApps_ordering_observability
* 05_ApplicationSet_Summary
