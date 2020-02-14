import pytest
import tango

@pytest.fixture(scope="class")
def midcsp_master():
    csp_master_proxy = tango.DeviceProxy("mid_csp/elt/master")
    return csp_master_proxy

@pytest.fixture(scope="class")
def midcsp_subarray01():
    csp_subarray01_proxy = tango.DeviceProxy("mid_csp/elt/subarray_01")
    return csp_subarray01_proxy

@pytest.fixture(scope="class")
def midcsp_subarray02():
    csp_subarray01_proxy = tango.DeviceProxy("mid_csp/elt/subarray_02")
    return csp_subarray02_proxy

@pytest.fixture(scope="class")
def midcsp_subarray03():
    csp_subarray01_proxy = tango.DeviceProxy("mid_csp/elt/subarray_03")
    return csp_subarray03_proxy
