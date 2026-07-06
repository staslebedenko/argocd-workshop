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

* [01_Intro_Apps_K8s_Tools_Argo](01_Intro_Apps_K8s_Tools_Argo/readme.md) - what GitOps is, provisioning AKS, installing Argo CD, and the sample apps we'll deploy throughout the workshop.
* [02_Argo_Projects_User_Kustomize](02_Argo_Projects_User_Kustomize/readme.md) - restricting the default Argo CD project, adding a scoped user/project, and Kustomize base/overlay basics.
* [03_App_deployment_first_issues](03_App_deployment_first_issues/readme.md) - deploying your first app via Argo CD Applications, and debugging real sync/health errors (paths, projects, namespace drift) as they happen.
* [04_AppOfApps_ordering_observability](04_AppOfApps_ordering_observability/readme.md) - splitting infra/app repos, the App-of-Apps pattern, sync-wave ordering, and basic observability.
* [05_ApplicationSet_Summary](05_ApplicationSet_Summary/readme.md) - replacing repetitive Application manifests with a single ApplicationSet, plus a wrap-up of the whole workshop.
