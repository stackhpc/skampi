import random
import string
from io import StringIO

import pytest
import yaml


@pytest.mark.no_deploy
def test_pvc_reclaim_policy_is_set_to_recycle(helm_adaptor):
    pv_resource_def = helm_adaptor.template('logging', give_a_release_name(), 'elastic-pv.yaml')
    resources_defs = [t for t in yaml.safe_load_all(StringIO(pv_resource_def)) if t is not None]

    assert resources_defs[0]['spec']['persistentVolumeReclaimPolicy'] == 'Recycle'


def give_a_release_name():
    word = ''.join([random.choice(list(string.ascii_lowercase)) for _ in range(7)])
    return word
