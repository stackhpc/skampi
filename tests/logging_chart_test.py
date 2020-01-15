import logging
import socket
import subprocess
from datetime import datetime
from io import StringIO
from time import sleep

import pytest
import requests
import yaml

from tests.testsupport.helm import HelmChart, ChartDeployment


@pytest.fixture(scope="module")
def logging_chart(helm_adaptor):
    return HelmChart('logging', helm_adaptor)


@pytest.mark.no_deploy
def test_pvc_reclaim_policy_is_set_to_recycle(logging_chart):
    resources = parse_yaml_str(logging_chart.templates['elastic-pv.yaml'])

    assert resources[0]['spec']['persistentVolumeReclaimPolicy'] == 'Recycle'


@pytest.mark.no_deploy
def test_elastic_service_is_exposed_on_port_9200_for_all_k8s_nodes(logging_chart):
    elastic_svc = parse_yaml_str(logging_chart.templates['elastic.yaml'])[1]

    expected_portmapping = {
        "port": 9200,
        "targetPort": 9200
    }

    assert elastic_svc['spec']['type'] == 'NodePort'
    assert expected_portmapping in elastic_svc['spec']['ports']


@pytest.mark.no_deploy
def test_elastic_curator_set_to_run_once_every_hour(logging_chart):
    curator_job = parse_yaml_str(logging_chart.templates['elastic_curator.yaml']).pop()

    assert curator_job['spec']['schedule'] == '0 1 * * *'


@pytest.mark.no_deploy
def test_fluentd_is_authorised_to_read_pods_and_namespaces_cluster_wide(logging_chart):
    serviceaccount, clusterrole, clusterrolebinding = parse_yaml_str(logging_chart.templates['fluentd-rbac.yaml'])
    daemonset = parse_yaml_str(logging_chart.templates['fluentd-daemonset.yaml']).pop()
    serviceaccount_name = serviceaccount['metadata']['name']

    expected_auth_rule = {
        "apiGroups": [""],
        "resources": ["pods", "namespaces"],
        "verbs": ["get", "list", "watch"]
    }

    assert expected_auth_rule in clusterrole['rules']
    assert serviceaccount_name in [s['name'] for s in clusterrolebinding['subjects']]
    assert daemonset['spec']['template']['spec']['serviceAccountName'] == serviceaccount_name


@pytest.mark.no_deploy
def test_fluentd_is_configured_to_integrate_with_elastic_via_incluster_hostname(logging_chart):
    elastic_deployment, elastic_svc = parse_yaml_str(logging_chart.templates['elastic.yaml'])
    fluentd_daemonset = parse_yaml_str(logging_chart.templates['fluentd-daemonset.yaml']).pop()

    expected_env_vars = [
        {"FLUENT_ELASTICSEARCH_HOST": elastic_deployment['metadata']['name']},
        {"FLUENT_ELASTICSEARCH_PORT": str(elastic_svc['spec']['ports'].pop()['port'])},
    ]

    fluentd_container = fluentd_daemonset['spec']['template']['spec']['containers'][0]
    env_vars = [{v['name']: v['value']} for v in fluentd_container['env']]

    for env_var in expected_env_vars:
        assert env_var in env_vars


@pytest.mark.chart_deploy
def test_fluentd_ingests_logs_from_pod_stdout_into_elasticsearch(logging_chart, helm_adaptor, k8s_api, test_namespace):
    # arrange:
    chart_deployment = ChartDeployment('logging', helm_adaptor, k8s_api)
    _deploy_echoserver(test_namespace)

    api_instance = k8s_api.CoreV1Api()
    elastic_svc_name = [svc.metadata.name for svc in api_instance.list_namespaced_service(test_namespace).items if
                        svc.metadata.name.startswith('elastic-')].pop()

    # TODO make port-forward idempotent
    subprocess.Popen(
        "kubectl port-forward -n {} svc/{} 9200:9200".format(test_namespace, elastic_svc_name).split())

    def elastic_proxy_is_ready():
        return check_connection('127.0.0.1', 9200)

    wait_until(elastic_proxy_is_ready)

    # act:
    start = datetime.now()
    expected_log = "simple were so well compounded"
    _print_to_stdout_in_cluster(expected_log)

    def fluentd_ingests_echoserver_logs():
        fluentd_daemonset_name = "daemonset/fluentd-logging-{}".format(chart_deployment.release_name)
        seconds_since_start = (datetime.now() - start).total_seconds()
        cmd = "kubectl logs {} -n {} --all-containers --since={}s | grep -q echoserver".format(fluentd_daemonset_name,
                                                                                               test_namespace,
                                                                                               seconds_since_start)
        return subprocess.run(cmd, shell=True).returncode == 0

    wait_until(fluentd_ingests_echoserver_logs)
    sleep(3)

    # assert:
    from elasticsearch import Elasticsearch
    es = Elasticsearch(['127.0.0.1:9200'], use_ssl=False, verify_certs=False, ssl_show_warn=False)

    query_body = {
        "query": {
            "match": {
                "log": expected_log
            }
        }
    }

    result = es.search(
        index="logstash-*",
        body=query_body
    )

    assert len(result['hits']['hits']) > 0


def _print_to_stdout_in_cluster(expected_log):
    requests.post("http://127.0.0.1:9001/echo", expected_log)


def _deploy_echoserver(test_namespace):
    subprocess.run("kubectl apply -n {} -f tests/testsupport/extras/echoserver.yaml".format(test_namespace).split(),
                   check=True)

    def echoserver_is_running():
        cmd = "kubectl describe pod echoserver -n {} | grep -q 'Status:.*Running'".format(
            test_namespace)
        return subprocess.run(cmd, shell=True).returncode == 0

    wait_until(echoserver_is_running)

    subprocess.Popen("kubectl port-forward -n {} pod/echoserver 9001:9001".format(test_namespace).split())

    def echoserver_proxy_is_ready():
        return check_connection('127.0.0.1', 9001)

    wait_until(echoserver_proxy_is_ready)


def check_connection(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex((host, port))
    s.close()
    return result == 0


def wait_until(test_cmd, retry_period=3, retry_timeout=30):
    assert callable(test_cmd)
    retry_start = datetime.now()
    while True:
        if test_cmd():
            break
        if (datetime.now() - retry_start).total_seconds() >= retry_timeout:
            raise TimeoutError(test_cmd)

        sleep(retry_period)


def parse_yaml_str(pv_resource_def):
    return [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]
