import logging
import json
import time
from datetime import datetime

import pytest
import kubernetes
from elasticsearch import Elasticsearch

from tests.testsupport.helm import ChartDeployment


@pytest.fixture(scope="module")
def logging_chart_deployment(helm_adaptor, k8s_api):
    logging.info("+++ Deploying logging chart.")
    chart_deployment = ChartDeployment('logging', helm_adaptor, k8s_api)
    yield chart_deployment
    logging.info("+++ Deleting logging chart release.")
    chart_deployment.delete()


@pytest.mark.quarantine
@pytest.mark.chart_deploy
def test_logs_getting_to_elastic(logging_chart_deployment, test_namespace):
    today_str = datetime.now().strftime("%Y.%m.%d")
    configuration = kubernetes.client.Configuration()
    api_instance = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(configuration))
    namespace = test_namespace
    timeout_seconds = 60
    api_response = api_instance.list_namespaced_pod(namespace, timeout_seconds=timeout_seconds)
    api_response_dict = api_response.to_dict()
    pod_names = [i['metadata']['name'] for i in api_response_dict['items']]
    logging.info("Running pods {}".format(pod_names))
    elastic_pod = [i for i in pod_names if 'elastic-logging' in i]
    assert pod_names
    assert elastic_pod
    elastic_pod_name = elastic_pod[0]
    command_str = 'curl -s  -X GET http://0.0.0.0:9200/logstash-{}/_count'.format(today_str)
    command = ['/bin/bash', '-c', command_str]
    logging.info("Test command: {}".format(command))

    for try_number in range(1,10):
        logging.info("Try number...{} of 9".format(try_number))
        resp = kubernetes.stream.stream(api_instance.connect_get_namespaced_pod_exec,
                                        elastic_pod_name,
                                        test_namespace,
                                        command=command,
                                        stderr=True, stdin=False,
                                        stdout=True, tty=False)
        resp = resp.replace("'", '"')
        logging.info("Response: " + resp)
        response_json = json.loads(resp)
        if 'error' in response_json:
            logging.info("Retrying")
            time.sleep(20)
            continue
        if 'count' in response_json and response_json['count'] == 0:
            logging.info("Retrying")
            time.sleep(5)
            continue
        break

    assert 'count' in response_json
    assert response_json['count'] > 0

    #Sample log
    command_str = ("curl -s  -X GET "
                   "http://0.0.0.0:9200/logstash-{}/_search?"
                   "q=kubernetes_namespace={}&size=1&pretty=true").format(today_str,
                                                                          test_namespace)
    command = ['/bin/bash', '-c', command_str]
    logging.info("Test command: {}".format(command))
    resp = kubernetes.stream.stream(api_instance.connect_get_namespaced_pod_exec,
                                        elastic_pod_name,
                                        test_namespace,
                                        command=command,
                                        stderr=True, stdin=False,
                                        stdout=True, tty=False)
    resp = resp.replace("'", '"')
    logging.info("Sample log: " + resp)
