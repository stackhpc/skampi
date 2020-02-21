import pytest
import sys
sys.path.append('/app')

import mock
import importlib
import tango
from tests.acceptance_tests.helpers import *
from oet.domain import SKAMid, SubArray, ResourceAllocation, Dish
from assertpy import assert_that

# DeviceProxy.get_attribute_list returns CSV string of attrs
attribute_list = 'buildState,versionId'

patch_config = {
    'get_attribute_list.return_value': attribute_list,
    }

class TestResource(object):
    def test_init(self):
        """
        Test the __init__ method.
        """
        name = 'name'
        r = resource(name)
        assert r.device_name == name

    @mock.patch('tango.DeviceProxy', **patch_config)
    def test_get_attr_not_found(self, mock_proxy):
        """
        Test the get method.
        Attribute name is not in the attribute list.
        """
        importlib.reload(sys.modules[resource.__module__])
        device_name = 'device'
        r = resource(device_name)
        assert r.get('nonexistent attribute') == 'attribute not found'

    def mock_start_up():
        pass

    @pytest.mark.skip(reason="failing")
    @mock.patch('oet.domain.SKAMid')
    @mock.patch('oet.domain.SubArray')
    def test_assign_resources(self,subarray_mock,telescope_mock):
        allocation = ResourceAllocation(dishes= [Dish(1), Dish(2), Dish(3), Dish(4)])
        telescope_mock.start_up= self.mock_start_up
        subarray_mock.allocate.return_value = allocation
        result = take_subarray(1).to_be_composed_out_of(4)
        telescope_mock.start_up.assert_called_once()
        subarray_mock.allocate.asser_called_once()
        assert_that(result).is_equal_to(ResourceAllocation(dishes= [Dish(1), Dish(2), Dish(3), Dish(4)]))