import pytest
import time
import logging
import tango
#from tango.test_context import DeviceTestContext

#import global_enum

def test_init_state(midcsp_master):
     time.sleep(2) 
     result = midcsp_master.state()
     assert result == tango.DevState.STANDBY

def test_csp_poweron_invalid_arg(midcsp_master):
    try: 
        result = midcsp_master.On(["cbf"])
    except tango.DevFailed as df:
        logging.warn(df.args[0].desc)
    start_time = time.time()
    timeout = False
    while True:
        state = midcsp_master.state()
        if state == tango.DevState.ON:
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 2:
            timeout = True
            break
    if not timeout:
        assert state == tango.DevState.ON
    else:
        assert state == tango.DevState.STANDBY

def test_poweron_csp(midcsp_master):
    try: 
         midcsp_master.On([])
    except tango.DevFailed as df:
        logging.warn(df.args[0].desc)
    start_time = time.time()
    timeout = False
    while True:
        state = midcsp_master.state()
        if state == tango.DevState.ON:
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 2:
            timeout = True
            break
    if not timeout:
        assert state == tango.DevState.ON
    else:
        assert state == tango.DevState.STANDBY

def test_csp_availableCapabilities(midcsp_master):
    availableCapabilities = midcsp_master.availableCapabilities
    assert availableCapabilities

def test_csp_receptorMembership(midcsp_master):
    receptorMembership = midcsp_master.receptorMembership
    assert not receptorMembership

def test_csp_unassignedReceptorIDs(midcsp_master):
    unassignedReceptorIDs = midcsp_master.unassignedReceptorIDs
    logging.info(tango.utils.info())
    logging.info(unassignedReceptorIDs)
    logging.info("type(unassignedReceptorIDs):{}".format(type(unassignedReceptorIDs)))
    assert len(unassignedReceptorIDs) 

