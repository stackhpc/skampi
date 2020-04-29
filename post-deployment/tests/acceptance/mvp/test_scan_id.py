#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_scan_id
----------------------------------
Acceptance tests for MVP.
"""
import sys

sys.path.append('/app')
import signal
from assertpy import assert_that
import pytest
from pytest_bdd import scenario, given, when, then

from oet.domain import SKAMid, SubArray
from resources.test_support.helpers import resource, watch, take_subarray, restart_subarray

def update_file(file_name):
    """Update configuration file"""
    import json
    import random
    from datetime import date
    with open(file_name, 'r') as file_object:
        data = json.load(file_object)
    parts = [
        "realtime",
        date.today().strftime("%Y%m%d"),
        str(random.choice(range(1, 10000))),
        ]
    data['sdp']['configure'][0]['id'] = '-'.join(parts)
    with open(file_name, 'w') as file_object:
        json.dump(data, file_object)

def handlde_timout():
    """Raise excepton for timeout"""
    print("operation timeout")
    raise Exception("operation timeout")

#@pytest.mark.xfail
@scenario("../../../features/scan_id.feature", "OET requests a scan ID")
def test_request_scan_id():
    """Test scan ID."""

@given("I am accessing the console interface for the OET")
def start_up():
    """Start up the telescope"""
    SKAMid().start_up()

@given("Sub-array is resourced")
def assign():
    """Assign resources to sub-array"""
    watch_receptor_id_list = watch(
        resource('ska_mid/tm_subarray_node/1')).for_a_change_on("receptorIDList")
    take_subarray(1).to_be_composed_out_of(4)
    watch_receptor_id_list.wait_until_value_changed()

@when("I call the configure scan execution instruction")
def config():
    """Configure sub-array"""
    # Update ID of config data to prevent sending duplicate configs during tests
    config_file = 'tests/acceptance_tests/test_data/polaris_b1_no_cam.json'
    update_file(config_file)
    # Set a timout mechanism in case a component gets stuck in executing
    signal.signal(signal.SIGALRM, handlde_timout)
    signal.alarm(60) # Wait for 30 seconds and timeout if still stick
    try:
        SubArray(1).configure_from_file(config_file)
    except:
        print("timeout")

@then("Sub-array is in READY state")
def check_state():
    """Ensure that the sub-array is in READY state"""
    # Check that the TMC reports READY observation state
    assert_that(resource('ska_mid/tm_subarray_node/1').get('obsState')).is_equal_to('READY')
    # Check that the CSP reports READY observation state
    assert_that(resource('mid_csp/elt/subarray_01').get('obsState')).is_equal_to('READY')
    # Check that the SDP reports READY observation state
    assert_that(resource('mid_sdp/elt/subarray_1').get('obsState')).is_equal_to('READY')

@then("Sub-array reports scan ID")
def check_scan_id():
    """Ensure that scan ID is as expected and has propagated through sub-array
    """
    # Check that the TMC reports scan ID
    assert_that(resource('ska_mid/tm_subarray_node/1').get('scanID')).is_equal_to('1')
    # Check that the CSP reports scan ID
    assert_that(resource('mid_csp/elt/subarray_01').get('scanId')).is_equal_to(1)
    # Check that the SDP reports scan ID
    #TODO add assert for SDP scan ID

def teardown_function(function):
    """Teardown any state that was previously setup with a setup_function call
    """
    if resource('ska_mid/tm_subarray_node/1').get('obsState') == "IDLE":
        SubArray(1).deallocate()
    if resource('ska_mid/tm_subarray_node/1').get('obsState') == "READY":
        SubArray(1).end_sb()
        SubArray(1).deallocate()
    if resource('ska_mid/tm_subarray_node/1').get('obsState') == "CONFIGURING":
        restart_subarray(1)
    SKAMid().standby()
