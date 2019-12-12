# -*- coding: utf-8 -*-
"""
A reimplementation of some of the basic tests in this directory, implemented using a bdd (Behaviour Driven Design) style. Currently, this is done by copy-paste of parts of the tests; it could reasonably be refactored to call the other functions more directly. However, I (vla22) wanted to partition the existing functions in a particular way, to fit better with the BDD style.
"""
import pytest
import itertools

from tango import Database, DeviceProxy
from time import sleep
from pytest_bdd import scenario, given, when, then


@scenario("./1.feature", "Test Tango setup")
def test_tango_setup():
    pass


@given("A set of tango devices", scope="session")
def devices_list():
    tangodb = Database()
    device_server_list = tangodb.get_server_list()

    device_classes_lists = [
            tangodb.get_device_class_list(device_server)
            for device_server in device_server_list ]

    # flatten the list of lists
    device_classes = list(itertools.chain.from_iterable(device_classes_lists))
 
    # remove tango-specifc "dogfood" devices
    device_names = [ 
            device_name for device_name in device_classes 
            if "dserver" not in device_name ]

    return device_classes


@when("I check the number of active devices")
def running_devices_count(devices_list):
    active_devices = []

    for device_name in devices_list:
        try:
            print("Connecting to '{}'...\r\n".format(device_name))
            device_client = DeviceProxy(device_name)
        except Exception as e:
            devices_list.remove(device_name) # remove inactive device
            print ("Could not connect to the '{}' Device.\r\n".format(device_name))
            print (e)

    print("Total number of active devices {}.".format(len(devices_list)))


@then("The number of active devices should be more than 50")
def assert_count(devices_list):
    assert len(devices_list) > 50
