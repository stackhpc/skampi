import socket
from datetime import datetime
from io import StringIO
from time import sleep

import yaml


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