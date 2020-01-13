import socket
import subprocess
from datetime import datetime
from io import StringIO
from time import sleep

import pytest
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
    echoserver_client = deploy_echoserver(test_namespace)

    api_instance = k8s_api.CoreV1Api()
    elastic_svc_name = [svc.metadata.name for svc in api_instance.list_namespaced_service(test_namespace).items if
                        svc.metadata.name.startswith('elastic-')].pop()

    # TODO make port-forward idempotent
    subprocess.run("kubectl port-forward svc/{} 9200:9200 --namespace {} &".format(elastic_svc_name, test_namespace),
                   shell=True)
    elastic_proxy_is_running = "nc -z 127.0.0.1 9200"
    wait_until(elastic_proxy_is_running)

    # act:
    expected_log = b"simple were so well compounded"
    echoserver_client.send(expected_log)
    sleep(10)  # allow log to propagate

    # assert:
    from elasticsearch import Elasticsearch
    es = Elasticsearch(['127.0.0.1:9200'], use_ssl=False, verify_certs=False, ssl_show_warn=False)

    query_body = {
        "query": {
            "match": {
                "log": {
                    "query": expected_log.decode('utf8')
                }
            }
        }
    }

    result = es.search(
        index="log*",
        body=query_body
    )

    assert len(result['hits']['hits']) > 0
    subprocess.run('kubectl delete job testhelper --namespace={}'.format(test_namespace).split(), check=True)
    subprocess.run('pkill kubectl'.split(), check=True)


def deploy_echoserver(test_namespace):
    local_proxy = '127.0.0.1'
    local_port = 9001

    subprocess.run("kubectl create -n {} -f tests/testsupport/extras/echoserver.yaml".format(test_namespace).split(),
                   check=True)
    pod_is_running = "kubectl describe pod echoserver -n {} | grep -q 'Status:.*Running'".format(
        test_namespace)
    wait_until(pod_is_running)

    subprocess.run("kubectl port-forward pod/echoserver {}:9001 --namespace {} &".format(local_port, test_namespace),
                   shell=True)
    proxy_is_running = "nc -z {} {}".format(local_proxy, local_port)
    wait_until(proxy_is_running)

    echoserver_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    echoserver_client.connect((local_proxy, local_port))
    return echoserver_client


def wait_until(test_cmd, retry_period=3, retry_timeout=30):
    retry_start = datetime.now()
    while True:
        pod_status = subprocess.run(
            test_cmd,
            shell=True, encoding='utf8', stdout=subprocess.PIPE)
        sleep(retry_period)
        if (pod_status.returncode == 0):
            break

        if (datetime.now() - retry_start).seconds >= retry_timeout:
            raise TimeoutError()


def parse_yaml_str(pv_resource_def):
    return [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]
