# Set dir of Makefile to a variable to use later
MAKEPATH := $(abspath $(lastword $(MAKEFILE_LIST)))
BASEDIR := $(notdir $(patsubst %/,%,$(dir $(MAKEPATH))))

# find IP addresses of this machine, setting THIS_HOST to the first address found
THIS_HOST := $(shell (ip a 2> /dev/null || ifconfig) | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY := $(THIS_HOST):0
XAUTHORITYx ?= ${XAUTHORITY}
KUBE_NAMESPACE ?= default## Kubernetes Namespace to use
HELM_RELEASE ?= test## Helm Chart release name
HELM_CHART ?= tango-base## Helm Chart to install (see ./charts)
HELM_CHART_TEST ?= tests## Helm Chart to install (see ./charts)
INGRESS_HOST ?= integration.engageska-portugal.pt ## Ingress HTTP hostname
USE_NGINX ?= false## Use NGINX as the Ingress Controller

# activate remote debugger for VSCode (ptvsd)
REMOTE_DEBUG ?= false

# define overides for above variables in here
-include PrivateRules.mak

.PHONY: vars k8s apply logs rm show deploy deploy_all delete ls podlogs namespace help helm_init helm_deploy helm_delete helm_test helm helm_deploy_all helm_delete_all
.DEFAULT_GOAL := help

#
# IMAGE_TO_TEST defines the tag of the Docker image to test
#
IMAGE_TO_TEST ?= nexus.engageska-portugal.pt/ska-docker/tango-itango
# Test runner - pod always running for testing purposes
TEST_RUNNER = test-runner-$(HELM_CHART_TEST)-$(HELM_RELEASE)
#
# defines a function to copy the ./test-harness directory into the K8s TEST_RUNNER
# and then runs the requested make target in the container.
# capture the output of the test in a build folder inside the container 
# 
k8s_test = kubectl exec -i $(TEST_RUNNER) --namespace $(KUBE_NAMESPACE) -- rm -fr /app/test-harness && \
		kubectl cp test-harness/ $(KUBE_NAMESPACE)/$(TEST_RUNNER):/app/test-harness && \
		kubectl exec -i $(TEST_RUNNER) --namespace $(KUBE_NAMESPACE) -- \
		/bin/bash -c "cd /app/test-harness && \
		make HELM_RELEASE=$(HELM_RELEASE) TANGO_HOST=databaseds-tango-base-$(HELM_RELEASE):10000 $1 && \
		mkdir build && \
		mv -f setup_py_test.stdout build && \
		mv -f report.json build && \
		mv -f report.xml build" \
		2>&1

# run the test function
# save the status
# clean out build dir
# retrieve the new build dir
# exit the saved status
k8s_test: ## test the application on K8s
	$(call k8s_test,test); \
	  status=$$?; \
	  rm -fr build; \
	  kubectl cp $(KUBE_NAMESPACE)/$(TEST_RUNNER):/app/test-harness/build/ build/; \
	  exit $$status


# stuff for backwards compatibility with helm v2
HELM_TILLER_PLUGIN := https://github.com/rimusz/helm-tiller
helm_is_v2 = $(strip $(shell helm version 2> /dev/null | grep SemVer:\"v2\.))
helm_install_shim = $(if $(helm_is_v2), --name $(HELM_RELEASE) --tiller-namespace $(KUBE_NAMESPACE), $(HELM_RELEASE))

# helm command to install a chart
# usage: $(call helm_install_cmd,$(HELM_CHART))
FULL_RELEASE_NAME := $(HELM_CHART)-$(HELM_RELEASE)
helm_install_cmd = helm install $(if helm_is_v2,,$(HELM_RELEASE)) charts/$1 \
		   	$(if helm_is_v2,--name $1-$(HELM_RELEASE) --tiller-namespace $(KUBE_NAMESPACE)) \
			--namespace="$(KUBE_NAMESPACE)" \
			--set display="$(DISPLAY)" \
			--set xauthority="$(XAUTHORITYx)" \
			--set ingress.hostname="$(INGRESS_HOST)" \
			--set ingress.nginx="$(USE_NGINX)" \
			--set tangoexample.debug="$(REMOTE_DEBUG)" \
			--set tests.enabled=true

# helm command to test a release
# usage: $(call helm_test_cmd)
helm_test_cmd = helm test $(FULL_RELEASE_NAME) $(if helm_is_v2,--logs --cleanup)

# helm command to delete a release
# usage: $(call helm_test_cmd)
helm_delete_cmd = helm delete $(FULL_RELEASE_NAME) $(if helm_is_v2,--purge)

# start the third-party tiller plugin if helmv2
define tiller-plugin-startup
$(if $(helm_is_v2), 
	@echo "+++ helmv2 detected. Starting third-party tiller plugin."
	@helm tiller start-ci $(KUBE_NAMESPACE)
	$(eval $(shell helm tiller env))
)
endef

define tiller-plugin-teardown
$(if $(helm_is_v2),
	@helm tiller stop
)
endef

# ensure third-party tiller plugin is installed for helm v2:
# tiller is provided locally as a helm plugin instead of on the cluster
helm_init:
	@echo "+++ Checking your helm version."
	@if [ -n '$(helm_is_v2)' ] && ! helm plugin list | grep -q tiller ; then \
		echo "+++ Detected helm v2 and no tiller. Installing local tiller plugin."; \
		helm plugin install $(HELM_TILLER_PLUGIN); \
	else \
		echo "+++ Everything seems fine." ;\
	fi

# deploys/releases a chart via helm
# usage make helm_deploy HELM_RELEASE=demo HELM_CHART=logging
helm_deploy: 
	$(tiller-plugin-startup)
	@echo "+++ Deploying chart '$(HELM_CHART)' as release '$(HELM_RELEASE)'."
	@$(call helm_install_cmd,$(HELM_CHART))
	$(tiller-plugin-teardown)

# deploy all the charts
# usage: make helm_deploy_all
CHARTS := $(shell cd charts/ && ls -d *)
helm_deploy_all:
	$(tiller-plugin-startup)
	$(foreach chrt,$(CHARTS),$(call helm_install_cmd,$(chrt));)
	$(tiller-plugin-teardown)

helm_ls:
	$(tiller-plugin-startup)
	@helm ls
	$(tiller-plugin-teardown)


# tests a released helm chart. will deploy it if it isn't already there
# usage: make helm_test HELM_RELEASE=mytest HELM_CHART=logging
helm_test: 
	$(tiller-plugin-startup)
	@$(call helm_test_cmd)
	$(tiller-plugin-teardown)

# deletes a deployed/released chart
# usage: make helm_delete HELM_RELEASE=test
helm_delete:
	$(tiller-plugin-startup)
	@$(call helm_delete_cmd)
	$(tiller-plugin-teardown)

# deletes all releases specified by KUBE_NAMESPACE and then HELM_RELEASE
# usage: make helm_delete_all KUBE_NAMESPACE=test HELM_RELEASE=demo
helm_delete_all: delete_etcd
	$(tiller-plugin-startup)
	helm delete $$(helm ls -q --namespace=$(KUBE_NAMESPACE)) $(if $(helm_is_v2),--purge)
	$(tiller-plugin-teardown)

# wrapper for helm commands
# usage: make helm HELM_CMD="ls --all"
helm:
	$(tiller-plugin-startup)
	@helm $(HELM_CMD)
	$(tiller-plugin-teardown)


vars: ## Display variables - pass in DISPLAY and XAUTHORITY
	@echo "DISPLAY: $(DISPLAY)"
	@echo "XAUTHORITY: $(XAUTHORITYx)"
	@echo "Namespace: $(KUBE_NAMESPACE)"

k8s: ## Which kubernetes are we connected to
	@echo "Kubernetes cluster-info:"
	@kubectl cluster-info
	@echo ""
	@echo "kubectl version:"
	@kubectl version
	@echo ""
	@echo "Helm version:"
	@helm version --client

logs: ## POD logs for descriptor
	@for i in `kubectl -n $(KUBE_NAMESPACE) get pods -l group=example -o=name`; \
	do echo "-------------------"; \
	echo "Logs for $$i"; \
	kubectl -n $(KUBE_NAMESPACE) logs $$i; \
	done
   
namespace: ## create the kubernetes namespace
	@kubectl describe namespace $(KUBE_NAMESPACE) > /dev/null 2>&1 ; \
  K_DESC=$$? ; \
  if [ $$K_DESC -eq 0 ] ; \
  then kubectl describe namespace $(KUBE_NAMESPACE) ; \
  else kubectl create namespace $(KUBE_NAMESPACE); \
  fi

lint_all:  ## lint ALL of the helm chart
	@for i in charts/*; do \
	cd $$i; pwd; helm lint ; \
	done

lint:  ## lint the HELM_CHART of the helm chart
	cd charts/$(HELM_CHART); pwd; helm lint;

.PHONY: deploy_etcd delete_etcd
deploy_etcd: ## deploy etcd-operator into namespace
	@if ! kubectl get pod -n $(KUBE_NAMESPACE) -o jsonpath='{.items[*].metadata.labels.app}' \
	     | grep -q etcd-operator; then \
		TMP=`mktemp -d`; \
		helm fetch stable/etcd-operator --untar --untardir $$TMP && \
		helm template $(helm_install_shim) $$TMP/etcd-operator -n etc-operator --namespace $(KUBE_NAMESPACE) \
		| kubectl apply -n $(KUBE_NAMESPACE) -f -; \
		rm -rf $$TMP; \
		n=5; \
        while ! kubectl api-resources --api-group=etcd.database.coreos.com \
           | grep -q etcdcluster && [ $${n} -gt 0 ]; do \
        	echo Waiting for etcd CRD to become available...; sleep 1; \
            n=`expr $$n - 1` || true; \
        done \
	fi

delete_etcd: ## Remove etcd-operator from namespace
	@if kubectl get pod -n $(KUBE_NAMESPACE) \
                   -o jsonpath='{.items[*].metadata.labels.app}' \
	   | grep -q etcd-operator; then \
		TMP=`mktemp -d`; \
		helm fetch stable/etcd-operator --untar --untardir $$TMP && \
		helm template $(helm_install_shim) $$TMP/etcd-operator -n etc-operator \
		| kubectl delete -n $(KUBE_NAMESPACE) -f -; \
		rm -rf $$TMP; \
	fi

mkcerts:  ## Make dummy certificates for $(INGRESS_HOST) and Ingress
	@if [ ! -f charts/webjive/data/tls.key ]; then \
	CN=`echo "$(INGRESS_HOST)" | tr -d '[:space:]'`; \
	openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 \
	   -keyout charts/webjive/data/tls.key \
		 -out charts/webjive/data/tls.crt \
		 -subj "/CN=$${CN}/O=Minikube"; \
	else \
	echo "SSL cert already exits in charts/webjive/data ... skipping"; \
	fi

deploy: namespace mkcerts  ## deploy the helm chart
	@helm template $(helm_install_shim) charts/$(HELM_CHART)/ \
				 --namespace $(KUBE_NAMESPACE) \
	             --set display="$(DISPLAY)" \
	             --set xauthority="$(XAUTHORITYx)" \
				 --set ingress.hostname=$(INGRESS_HOST) \
				 --set ingress.nginx=$(USE_NGINX) \
	             --set tangoexample.debug="$(REMOTE_DEBUG)" | kubectl apply -f -

show: mkcerts  ## show the helm chart
	@helm template $(helm_install_shim) charts/$(HELM_CHART)/ \
				 --namespace $(KUBE_NAMESPACE) \
	             --set display="$(DISPLAY)" \
	             --set xauthority="$(XAUTHORITYx)" \
				 --set ingress.hostname=$(INGRESS_HOST) \
				 --set ingress.nginx=$(USE_NGINX) \
	             --set tangoexample.debug="$(REMOTE_DEBUG)"

delete: ## delete the helm chart release
	@helm template $(helm_install_shim) charts/$(HELM_CHART)/ \
				 --namespace $(KUBE_NAMESPACE) \
	             --tiller-namespace $(KUBE_NAMESPACE) \
	             --set display="$(DISPLAY)" \
	             --set xauthority="$(XAUTHORITYx)" \
				 --set ingress.hostname=$(INGRESS_HOST) \
				 --set ingress.nginx=$(USE_NGINX) \
	             --set tangoexample.debug="$(REMOTE_DEBUG)" | kubectl delete -f -

deploy_all: namespace mkcerts deploy_etcd  ## deploy ALL of the helm chart
	@for i in charts/*; do \
	helm template $(helm_install_shim) $$i \
				 --namespace $(KUBE_NAMESPACE) \
	             --tiller-namespace $(KUBE_NAMESPACE) \
	             --set display="$(DISPLAY)" \
	             --set xauthority="$(XAUTHORITYx)" \
				 --set ingress.hostname=$(INGRESS_HOST) \
				 --set ingress.nginx=$(USE_NGINX) \
	             --set tangoexample.debug="$(REMOTE_DEBUG)" | kubectl apply -f - ; \
	done

delete_all: delete_etcd ## delete ALL of the helm chart release
	@for i in charts/*; do \
	helm template $(helm_install_shim) $$i \
				 --namespace $(KUBE_NAMESPACE) \
	             --set display="$(DISPLAY)" \
	             --set xauthority="$(XAUTHORITYx)" \
				 --set ingress.hostname=$(INGRESS_HOST) \
				 --set ingress.nginx=$(USE_NGINX) \
	             --set tangoexample.debug="$(REMOTE_DEBUG)" | kubectl delete -f - ; \
	done

poddescribe: ## describe Pods executed from Helm chart
	@for i in `kubectl -n $(KUBE_NAMESPACE) get pods -l release=$(HELM_RELEASE) -o=name`; \
	do echo "---------------------------------------------------"; \
	echo "Describe for $${i}"; \
	echo kubectl -n $(KUBE_NAMESPACE) describe $${i}; \
	echo "---------------------------------------------------"; \
	kubectl -n $(KUBE_NAMESPACE) describe $${i}; \
	echo "---------------------------------------------------"; \
	echo ""; echo ""; echo ""; \
	done

podlogs: ## show Helm chart POD logs
	@for i in `kubectl -n $(KUBE_NAMESPACE) get pods -l release=$(HELM_RELEASE) -o=name`; \
	do \
	echo "---------------------------------------------------"; \
	echo "Logs for $${i}"; \
	echo kubectl -n $(KUBE_NAMESPACE) logs $${i}; \
	echo kubectl -n $(KUBE_NAMESPACE) get $${i} -o jsonpath="{.spec.initContainers[*].name}"; \
	echo "---------------------------------------------------"; \
	for j in `kubectl -n $(KUBE_NAMESPACE) get $${i} -o jsonpath="{.spec.initContainers[*].name}"`; do \
	RES=`kubectl -n $(KUBE_NAMESPACE) logs $${i} -c $${j} 2>/dev/null`; \
	echo "initContainer: $${j}"; echo "$${RES}"; \
	echo "---------------------------------------------------";\
	done; \
	echo "Main Pod logs for $${i}"; \
	echo "---------------------------------------------------"; \
	for j in `kubectl -n $(KUBE_NAMESPACE) get $${i} -o jsonpath="{.spec.containers[*].name}"`; do \
	RES=`kubectl -n $(KUBE_NAMESPACE) logs $${i} -c $${j} 2>/dev/null`; \
	echo "Container: $${j}"; echo "$${RES}"; \
	echo "---------------------------------------------------";\
	done; \
	echo "---------------------------------------------------"; \
	echo ""; echo ""; echo ""; \
	done

localip:  ## set local Minikube IP in /etc/hosts file for Ingress $(INGRESS_HOST)
	@new_ip=`minikube ip` && \
	existing_ip=`grep $(INGRESS_HOST) /etc/hosts || true` && \
	echo "New IP is: $${new_ip}" && \
	echo "Existing IP: $${existing_ip}" && \
	if [ -z "$${existing_ip}" ]; then echo "$${new_ip} $(INGRESS_HOST)" | sudo tee -a /etc/hosts; \
	else sudo perl -i -ne "s/\d+\.\d+.\d+\.\d+/$${new_ip}/ if /$(INGRESS_HOST)/; print" /etc/hosts; fi && \
	echo "/etc/hosts is now: " `grep $(INGRESS_HOST) /etc/hosts`

help:  ## show this help.
	@echo "make targets:"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ""; echo "make vars (+defaults):"
	@grep -E '^[0-9a-zA-Z_-]+ \?=.*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = " \\?\\= "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
