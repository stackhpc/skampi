import pytest
import sys
import os
import logging
import time
import numpy as np
import tango

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
    assert not any(receptorMembership)

def test_csp_unassignedReceptorIDs(midcsp_master):
    unassignedReceptorIDs = midcsp_master.unassignedReceptorIDs
    assert len(unassignedReceptorIDs) 

def test_csp_subarrays_state(midcsp_subarray01,  midcsp_subarray02):
    start_time = time.time()
    timeout = False
    while True:
        sub1_state = midcsp_subarray01.state()
        sub2_state = midcsp_subarray02.state()
        if ((sub1_state == tango.DevState.OFF) and (sub2_state == tango.DevState.OFF)):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 2:
            timeout = True
            break
    if not timeout:
        assert ((sub1_state == tango.DevState.OFF) and (sub2_state == tango.DevState.OFF))
    else:
        assert sub1_state == tango.DevState.DISABLE

def test_csp_add_invalid_receptor_ids(midcsp_subarray01, midcsp_master):
    """
    Test the assignment of a number of invalid receptor IDs to
    the MidCspSubarray01.
    The AddReceptors method fails raising a tango.DevFailed exception.
    """
    unassigned_receptors = midcsp_master.unassignedReceptorIDs
    # receptor_list is a numpy array
    # all(): test whether all array elements evaluate to True.
    assert len(unassigned_receptors) == 4
    invalid_receptor_to_assign = []
    # try to add 3 invalid receptors
    for id_num in range(1, 198):
        if id_num not in unassigned_receptors:
            invalid_receptor_to_assign.append(id_num)
        if len(invalid_receptor_to_assign) > 3:
            break
    logging.info("Receptors to add:{}".format(invalid_receptor_to_assign))
    midcsp_subarray01.AddReceptors(invalid_receptor_to_assign)
    time.sleep(1)
    unassigned_receptors = midcsp_master.unassignedReceptorIDs
    assert len(unassigned_receptors) == 4

def test_csp_add_receptors(midcsp_master, midcsp_subarray01, midcsp_subarray02):
    midcsp_subarray01.AddReceptors([1,2])
    midcsp_subarray02.AddReceptors([3,4])
    timeout = False
    start_time = time.time()
    while True:
        sub1_state = midcsp_subarray01.state()
        sub2_state = midcsp_subarray02.state()
        if ((sub1_state == tango.DevState.ON) and
           (sub2_state == tango.DevState.ON)):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 2:
            timeout = True
            break
    if not timeout:
        assert (sub1_state == tango.DevState.ON) and (sub2_state == tango.DevState.ON)
        logging.info("Elapsed_time:{}".format(time.time() - start_time))
    else:
        assert 0
    assignedReceptors_1 = midcsp_subarray01.assignedReceptors
    assignedReceptors_2 = midcsp_subarray02.assignedReceptors
    assert len(assignedReceptors_1) == 2
    assert len(assignedReceptors_2) == 2
    timeout = False
    start_time = time.time()
    while True:
        receptorMembership = midcsp_master.receptorMembership
        if np.array_equal(receptorMembership, [1,1,2,2]):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 2:
            timeout = True 
            break
    logging.info("add_receptors: receptorMembership: {}".format(receptorMembership))
    assert np.array_equal(receptorMembership, [1,1,2,2])

def test_csp_add_already_assigned_receptors(midcsp_master, midcsp_subarray01):
    sub1_state = midcsp_subarray01.state()
    assert sub1_state == tango.DevState.ON
    receptorMembership = midcsp_master.receptorMembership
    logging.info("already_assigned:receptorMembership: {}".format(receptorMembership))
    midcsp_subarray01.AddReceptors([3,4])
    time.sleep(2)
    assignedReceptors_1 = midcsp_subarray01.assignedReceptors
    num_receptors = len(assignedReceptors_1)
    assert num_receptors == 2

def test_subarrays_state_after_receptors_assignment(midcsp_subarray01, midcsp_subarray02):
    """
    Test the CspSubarray State after receptors assignment.
    After assignment State is ON
    """
    # read the list of assigned receptors and check it's not
    # empty
    assigned_receptors1 = midcsp_subarray01.assignedReceptors
    assigned_receptors2 = midcsp_subarray02.assignedReceptors
    assert assigned_receptors1.any()
    assert assigned_receptors2.any()
    # read the CspSubarray State
    sub1_state = midcsp_subarray01.state()
    sub2_state = midcsp_subarray02.state()
    assert ((sub1_state == tango.DevState.ON) and (sub2_state == tango.DevState.ON))

def test_csp_remove_receptors(midcsp_master, midcsp_subarray01, midcsp_subarray02):
    midcsp_subarray01.RemoveReceptors([1,])
    midcsp_subarray02.RemoveReceptors([4,])
    timeout = False
    start_time = time.time()
    while True:
        receptorMembership = midcsp_master.receptorMembership
        logging.info("remove receptors receptorMembership:{}".format(receptorMembership))
        if np.array_equal(receptorMembership, [0,1,2,0]):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 3:
            timeout = True
            break
    assert np.array_equal(receptorMembership, [0,1,2,0])

def test_csp_remove_all_receptors(midcsp_master, midcsp_subarray01, midcsp_subarray02):
    midcsp_subarray01.RemoveAllReceptors()
    midcsp_subarray02.RemoveAllReceptors()
    timeout = False
    start_time = time.time()
    while True:
        receptorMembership = midcsp_master.receptorMembership
        logging.info("remove receptors receptorMembership:{}".format(receptorMembership))
        if np.array_equal(receptorMembership, [0,0,0,0]):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 3:
            timeout = True
            break
    logging.info("Elapsed_time:{}".format(time.time() - start_time))
    assert np.array_equal(receptorMembership, [0,0,0,0])

def test_subarrays_state_after_remove_receptors(midcsp_subarray01, midcsp_subarray02):
    """
    Test the CspSubarray State after receptors assignment.
    After assignment State is ON
    """
    # read the list of assigned receptors and check it's not
    # empty
    assigned_receptors1 = midcsp_subarray01.assignedReceptors
    assigned_receptors2 = midcsp_subarray02.assignedReceptors
    logging.info("assigned_receptors1:{}".format(assigned_receptors1))
    logging.info("assigned_receptors2:{}".format(assigned_receptors2))
    assert not assigned_receptors1.any()
    assert not assigned_receptors2.any()
    # read the CspSubarray State
    sub1_state = midcsp_subarray01.state()
    sub2_state = midcsp_subarray02.state()
    logging.info("sub1_state:{}".format(sub1_state))
    logging.info("sub2_state:{}".format(sub2_state))
    assert sub1_state == tango.DevState.OFF
    assert sub2_state == tango.DevState.OFF

def test_configureScan_invalid_state(midcsp_subarray01):
    """
    Test that the ConfigureScan() command fails if the Subarray
    state is  not ON
    """
    # check the subarray state is Off (the previous test has removed
    # all the receptors from the subarray, so its state should be OFF
    sub1_state = midcsp_subarray01.state()
    logging.info("sub1_state:{}".format(sub1_state))
    assigned_receptors1 = midcsp_subarray01.assignedReceptors
    logging.info("assigned_receptors1:{}".format(assigned_receptors1))
    assert sub1_state == tango.DevState.OFF
    file_path = os.path.dirname(os.path.abspath(__file__))
    logging.info(file_path)
    f = open(file_path + "/data/configScan_sub1.json")
    with pytest.raises(tango.DevFailed) as df:
        midcsp_subarray01.ConfigureScan(f.read().replace("\n", ""))
        logging.info("Sono qui!!")
    if df:
        logging.info("configureScan_invalid_state:{}".format(df.value.args[0].desc))
        err_msg = str(df.value.args[0].desc)
        assert "Command ConfigureScan not allowed" in err_msg

def test_subarrays_configureScan(midcsp_subarray01, midcsp_subarray02, midcsp_master):
    """
    Test that the ConfigureScan() command is issued when the Subarray
    state is ON and ObsState is IDLE or READY
    """
    obs_state1 = midcsp_subarray01.obsState
    obs_state2 = midcsp_subarray02.obsState
    logging.info("obs_state1:{} obs_state2:{}".format(obs_state1, obs_state2))
    assert ((obs_state1 == 0) and (obs_state2 == 0))

    sub1_state = midcsp_subarray01.state()
    sub2_state = midcsp_subarray02.state()
    assert ((sub1_state == tango.DevState.OFF) and (sub2_state == tango.DevState.OFF))
    midcsp_subarray01.AddReceptors([1,4])
    midcsp_subarray02.AddReceptors([2,3])
    start_time = time.time()
    timeout = False
    while True:
        sub1_state = midcsp_subarray01.state()
        sub2_state = midcsp_subarray02.state()
        if ((sub1_state == tango.DevState.ON) and (sub2_state == tango.DevState.ON)):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > 3:
            timeout = True
            break
    assert not timeout
    time.sleep(2)
    midcsp_subarray01.configurationDelayExpected = 3
    midcsp_subarray02.configurationDelayExpected = 3
    config_delay = midcsp_subarray01.configurationDelayExpected
    file_path = os.path.dirname(os.path.abspath(__file__))
    f1 = open(file_path + "/data/configScan_sub1.json")
    f2 = open(file_path + "/data/configScan_sub2.json")
    midcsp_subarray01.ConfigureScan(f1.read().replace("\n", ""))
    midcsp_subarray02.ConfigureScan(f2.read().replace("\n", ""))
    f1.close()
    f2.close()
    start_time = time.time()
    timeout = False
    while True:
        obs_state1 = midcsp_subarray01.obsState
        obs_state2 = midcsp_subarray02.obsState
        if ((obs_state1 == 2) and (obs_state2 == 2)):
            break
        else:
            time.sleep(0.2)
        elapsed_time = time.time() - start_time
        if elapsed_time > config_delay * 1.5:
            timeout = True
            break
    logging.info("obs_state1:{} obs_State2:{}".format(obs_state1,obs_state2))
    timeout1 = midcsp_subarray01.timeoutExpiredFlag
    timeout2 = midcsp_subarray01.timeoutExpiredFlag
    assert (timeout1  and timeout2)
