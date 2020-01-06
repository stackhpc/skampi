import random
import string
from io import StringIO

import pytest
import yaml


@pytest.mark.no_deploy
def test_pvc_reclaim_policy_is_set_to_recycle(helm_adaptor):
    pv_resource_def = helm_adaptor.template('logging', give_any_release_name(), 'elastic-pv.yaml')
    resources = parse_yaml_str(pv_resource_def)

    assert resources[0]['spec']['persistentVolumeReclaimPolicy'] == 'Recycle'


def parse_yaml_str(pv_resource_def):
    return [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]


def give_any_release_name():
    return "{}-{}".format(_random_alpha(), _random_alpha())


def _random_alpha(length=7):
    return ''.join([random.choice(list(string.ascii_lowercase)) for _ in range(length)])
