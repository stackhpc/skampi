##the following section is for developers requiring the testing pod to be instantiated with a volume mappig to skampi
location:= $(shell pwd)
kube_path ?= $(shell echo ~/.kube)
k8_path ?= $(shell echo ~/.minikube)
PYTHONPATH=/home/tango/skampi/:/home/tango/skampi/post-deployment/:
testing-pod?=testing-pod
#the port mapping to host
hostPort ?= 2020
testing-config := '{ "apiVersion": "v1","spec":{\
					"containers":[{\
						"image":"$(IMAGE_TO_TEST)",\
						"name":"testing-container",\
						"volumeMounts":[{\
							"mountPath":"/home/tango/skampi/",\
							"name":"testing-volume"}],\
						"env":[{\
          			 		"name": "TANGO_HOST",\
            				"value": "databaseds-tango-base-$(HELM_RELEASE):10000"},{\
							"name": "KUBE_NAMESPACE",\
          					"value": "$(KUBE_NAMESPACE)"},{\
        					"name": "HELM_RELEASE",\
          					"value": "$(HELM_RELEASE)"},{\
							"name": "PYTHONPATH",\
							"value": "$(PYTHONPATH)"}],\
						"ports":[{\
							"containerPort":22,\
							"hostPort":$(hostPort)}]}],\
					"volumes":[{\
						"name":"testing-volume",\
						"hostPath":{\
							"path":"$(location)",\
							"type":"Directory"}}]}}'

GIT_EMAIL?=user.email.com
GIT_USER?="user name"

deploy_testing_pod:
	@kubectl run $(testing-pod) \
		--image=$(IMAGE_TO_TEST) \
		--namespace $(KUBE_NAMESPACE) \
		--wait \
		--generator=run-pod/v1 \
		--overrides=$(testing-config)
	@kubectl wait --for=condition=Ready pod/$(testing-pod)
	@kubectl exec -it $(testing-pod) -- bash -c "/usr/bin/python3 -m pip install -r /home/tango/skampi/post-deployment/test_requirements.txt"
	@kubectl cp $(kube_path) $(KUBE_NAMESPACE)/$(testing-pod):/home/tango/.kube/ 
	@kubectl cp $(k8_path) $(KUBE_NAMESPACE)/$(testing-pod):/home/tango/.minikube/
	@kubectl exec -it $(testing-pod) -- bash -c " \
		kubectl config --kubeconfig=/home/tango/.kube/config set-credentials minikube --client-key=/home/tango/.minikube/client.key && \
		kubectl config --kubeconfig=/home/tango/.kube/config set-credentials minikube --client-certificate=/home/tango/.minikube/client.crt && \
		kubectl config --kubeconfig=/home/tango/.kube/config set-cluster minikube --certificate-authority=/home/tango/.minikube/ca.crt && \
		echo 'source <(kubectl completion bash)' >>/home/tango/.bashrc && \
		echo 'export HELM_RELEASE=$(HELM_RELEASE)' >> /home/tango/.bashrc && \
		echo 'export KUBE_NAMESPACE=$(KUBE_NAMESPACE)' >> /home/tango/.bashrc && \
		echo 'export GIT_EMAIL=$(GIT_EMAIL)' >> /home/tango/.bashrc && \
		echo 'export GIT_USER=$(GIT_USER)' >> /home/tango/.bashrc && \
		echo 'export VALUES=pipeline.yaml' >> /home/tango/.bashrc && \
		echo 'export TANGO_HOST=databaseds-tango-base-test:10000' >> /home/tango/.bashrc "

	
delete_testing_pod:
	@kubectl delete pod $(testing-pod) --namespace $(KUBE_NAMESPACE)

attach_testing_pod:
	@kubectl exec -it $(testing-pod) --namespace $(KUBE_NAMESPACE) /bin/bash


clean_skampi:
	 git ls-files . --ignored --exclude-standard --others --directory | xargs rm -R -f

ssh_config = "Host kube-host\n\tHostName $(THIS_HOST) \n \tUser ubuntu"

test_as_ssh_client:
	@kubectl exec -it $(testing-pod) -- bash -c "mkdir /home/tango/.ssh/ && ssh-keygen -t rsa -f /home/tango/.ssh/id_rsa -q -P ''"
	@kubectl exec -it $(testing-pod) -- bash -c "cat /home/tango/.ssh/id_rsa.pub" >>~/.ssh/authorized_keys
	@kubectl exec -it $(testing-pod) -- bash -c "chown tango:tango -R /home/tango/.ssh/"
	@echo $(ssh_config) >temp
	@kubectl cp temp $(KUBE_NAMESPACE)/$(testing-pod):/home/tango/.ssh/config
	@rm temp


config_git:
	git config --global user.name '$(GIT_USER)'
	git config --global user.email $(GIT_EMAIL)

check_log_consumer_running:
	ps aux | awk 