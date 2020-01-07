import glob
import os
import random
import string
from io import StringIO

import pytest
import yaml


class HelmChart(object):

    def __init__(self, name, helm_adaptor):
        self.name = name
        self.templates_dir = "charts/{}/templates".format(self.name)
        self._helm_adaptor = helm_adaptor
        self._release_name_stub = self.generate_release_name()
        self._rendered_templates = None

    @property
    def templates(self):
        if self._rendered_templates is not None:
            return self._rendered_templates

        chart_templates = [os.path.basename(fpath) for fpath in (glob.glob("{}/*.yaml".format(self.templates_dir)))]
        self._rendered_templates = {template: self._helm_adaptor.template(self.name, self._release_name_stub, template)
                                    for template in
                                    chart_templates}
        return self._rendered_templates

    @staticmethod
    def generate_release_name():
        def random_alpha(length=7):
            return ''.join([random.choice(list(string.ascii_lowercase)) for _ in range(length)])

        return "{}-{}".format(random_alpha(), random_alpha())


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


def parse_yaml_str(pv_resource_def):
    return [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]
