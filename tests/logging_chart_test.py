import socket
import subprocess
from datetime import datetime
from io import StringIO
from time import sleep

import pytest
import requests
import yaml
from elasticsearch import Elasticsearch

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


@pytest.fixture(scope="module")
def logging_chart_deployment(helm_adaptor, k8s_api):
    chart_deployment = ChartDeployment('logging', helm_adaptor, k8s_api)
    yield chart_deployment
    chart_deployment.delete()


@pytest.fixture(scope="module")
def echoserver(test_namespace):
    echoserver = EchoServer(test_namespace)
    yield echoserver
    echoserver.delete()


def test_fluentd_ingests_logs_from_pod_stdout_into_elasticsearch(logging_chart_deployment, echoserver, test_namespace):
    # arrange:
    _proxy_elastic_service(_get_elastic_svc_name(logging_chart_deployment), test_namespace)

    # act:
    expected_log = "simple were so well compounded"
    echoserver.print_to_stdout(expected_log)
    fluentd_daemonset_name = "daemonset/fluentd-logging-{}".format(logging_chart_deployment.release_name)
    _wait_until_fluentd_ingests_echoserver_logs(
        fluentd_daemonset_name, datetime.now(), test_namespace)

    # assert:
    result = _query_elasticsearch_for_log(expected_log)
    assert len(result['hits']['hits']) > 0


def _proxy_elastic_service(elastic_svc_name, test_namespace):
    # TODO make port-forward idempotent
    subprocess.Popen(
        "kubectl port-forward -n {} svc/{} 9200:9200".format(test_namespace, elastic_svc_name).split())

    def elastic_proxy_is_ready():
        return check_connection('127.0.0.1', 9200)

    wait_until(elastic_proxy_is_ready)


def _get_elastic_svc_name(logging_chart_deployment):
    # TODO resolve this name statically from HelmChart() instance
    elastic_svc_name = [svc.metadata.name for svc in logging_chart_deployment.get_services() if
                        svc.metadata.name.startswith('elastic-')].pop()
    return elastic_svc_name


def _wait_until_fluentd_ingests_echoserver_logs(fluentd_daemonset_name, start_timestamp, namespace):
    def fluentd_ingests_echoserver_logs():
        seconds_since_start = (datetime.now() - start_timestamp).total_seconds()
        cmd = "kubectl logs {} -n {} --all-containers --since={}s | grep -q echoserver".format(fluentd_daemonset_name,
                                                                                               namespace,
                                                                                               int(seconds_since_start))
        return subprocess.run(cmd, shell=True).returncode == 0

    wait_until(fluentd_ingests_echoserver_logs, retry_timeout=60)
    sleep(5)


def _query_elasticsearch_for_log(log_msg):
    es = Elasticsearch(['127.0.0.1:9200'], use_ssl=False, verify_certs=False, ssl_show_warn=False)
    query_body = {
        "query": {
            "match": {
                "log": log_msg
            }
        }
    }
    result = es.search(
        index="logstash-*",
        body=query_body
    )
    return result


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
        if int((datetime.now() - retry_start).total_seconds()) >= retry_timeout:
            raise TimeoutError(test_cmd)

        sleep(retry_period)


def parse_yaml_str(pv_resource_def):
    return [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]


class EchoServer(object):
    DEFINITION_FILE = 'tests/testsupport/extras/echoserver.yaml'
    LISTEN_PORT = 9001

    def __init__(self, namespace):
        with open(self.DEFINITION_FILE, 'r') as f:
            self.definition = parse_yaml_str(f.read())
        self.namespace = namespace

        self._deploy()
        self._proxy()

    def _deploy(self, wait=True):
        subprocess.run("kubectl apply -n {} -f {}".format(self.namespace, self.DEFINITION_FILE).split(),
                       check=True)
        if wait:
            wait_until(self.is_running)

    def _proxy(self, wait=True):
        subprocess.Popen(
            "kubectl port-forward -n {0} pod/echoserver {1}:{1}".format(self.namespace, self.LISTEN_PORT).split())

        if wait:
            wait_until(self.is_proxied_locally)

    def print_to_stdout(self, line):
        requests.post("http://127.0.0.1:{}/echo".format(self.LISTEN_PORT), line)

    def delete(self):
        for resource in self.definition:
            subprocess.run(
                "kubectl delete {} {} -n {} --force --grace-period=0".format(resource['kind'],
                                                                             resource['metadata']['name'],
                                                                             self.namespace).split(), check=True)

    def is_running(self):
        cmd = "kubectl describe pod echoserver -n {} | grep -q 'Status:.*Running'".format(
            self.namespace)
        return subprocess.run(cmd, shell=True).returncode == 0

    def is_proxied_locally(self):
        return check_connection('127.0.0.1', self.LISTEN_PORT)
