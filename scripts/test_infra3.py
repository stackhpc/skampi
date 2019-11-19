from __future__ import print_function
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import time

#taken from https://medium.com/programming-kubernetes/building-stuff-with-the-kubernetes-api-part-3-using-python-aea5ab16f627
print("hello")
def test_pods_ok():
    config.load_kube_config()
    #comment out line above and uncomment line below if deploying on cluster
    #config.load_inclster_config()
    api = client.CoreV1Api()
    print("should have config")
    namespace = "integration"
    pretty = "true"
    _continue = '_continue_example'
    limit = 100
    timeout_seconds = 56
    field_selector1 = "status.phase=Running"
    field_selector2 = "status.phase=Succeeded"

    try:
        list_of_pods = api.list_namespaced_pod(namespace=namespace, limit=limit, timeout_seconds=timeout_seconds)
        pods_dict = list_of_pods.to_dict()
        how_many_pods = len(pods_dict['items'])
        print(how_many_pods)
        running_pods = api.list_namespaced_pod(namespace=namespace, field_selector=field_selector1, limit=limit, timeout_seconds=timeout_seconds)
        completed_pods = api.list_namespaced_pod(namespace=namespace, field_selector=field_selector2, limit=limit, timeout_seconds=timeout_seconds)
        run_pods_dict = running_pods.to_dict()
        completed_dict = completed_pods.to_dict()
        how_many_run = len(run_pods_dict['items'])
        how_many_completed = len(completed_dict['items'])
        assert (how_many_run + how_many_completed) == how_many_pods

            
    except ApiException as e:
        print("Exception when calling CoreV1Api->list_namespaced_pod: %s\n" %e)

if __name__ == '__main__':
    test_pods_ok()
