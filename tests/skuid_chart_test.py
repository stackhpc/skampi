import logging
import json

import pytest

from tests.testsupport.helm import ChartDeployment


@pytest.fixture(scope="class")
def skuid_chart_deployment(helm_adaptor, k8s_api):
    logging.info("+++ Deploying skuid chart.")
    chart_deployment = ChartDeployment("skuid", helm_adaptor, k8s_api)
    yield chart_deployment
    logging.info("+++ Deleting logging chart release.")
    chart_deployment.delete()


@pytest.mark.chart_deploy
@pytest.mark.usefixtures("skuid_chart_deployment")
class TestSkuidDeployment:
    def test_skuid_is_up_and_serving(self, skuid_chart_deployment):
        """Check that skuid is up and base path is as expected"""
        skuid_pod_name = skuid_chart_deployment.search_pod_name("skuid-deployment")[0]
        command_str = "curl -s  -X GET " "http://0.0.0.0:9870/skuid"

        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)
        assert "Welcome to skuid" in resp

        command_str = "curl -s  -X GET " "http://0.0.0.0:9870/skuid"
        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)

        command_str = "curl -s  -X GET " "http://0.0.0.0:9870/skuid/ska_id/test"
        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)
        resp_json = json.loads(resp)
        resp_json = json.loads(resp_json)
        assert "ska_uid" in resp_json
        assert "generator_id" in resp_json
        assert resp_json["generator_id"] == "T0001"
        assert "test:T0001" in resp_json["ska_uid"]

        command_str = "curl -s  -X GET " "http://0.0.0.0:9870/skuid/ska_scan_id"
        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)
        resp_json = json.loads(resp)
        resp_json = json.loads(resp_json)

        command_str = "curl -s  -X GET " "http://0.0.0.0:9870/skuid/entity_types/get"
        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)
        resp_json = json.loads(resp)
        resp_json = json.loads(resp_json)
        assert len(resp_json) > 5

        command_str = (
            "curl -s  -X POST " "http://0.0.0.0:9870/skuid/entity_types/add/new"
        )
        resp = skuid_chart_deployment.pod_exec_bash(skuid_pod_name, command_str)
        resp_json = json.loads(resp)
        resp_json = json.loads(resp_json)
        assert "new" in resp_json
