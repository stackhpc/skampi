# -*- coding: utf-8 -*-
"""
Test archiver
"""
from tango import DevFailed, DeviceProxy, GreenMode, AttributeProxy, ApiUtil, DeviceData
from time import sleep
import pytest
import logging
import sys

@pytest.mark.archiver
def test_init():
  print("Init test archiver")
  evt_subscriber_device_fqdn = "archiving/hdbpp/eventsubscriber01"
  evt_subscriber_device_proxy = DeviceProxy(evt_subscriber_device_fqdn)
  evt_subscriber_device_proxy.Start()
  sleep(3) # the polling

def configure_attribute(attribute):
  conf_manager_proxy = DeviceProxy("archiving/hdbpp/confmanager01")
  
  #logging.info(conf_manager_proxy.Status())

  evt_subscriber_device_fqdn = "archiving/hdbpp/eventsubscriber01"
  evt_subscriber_device_proxy = DeviceProxy(evt_subscriber_device_fqdn)

  is_already_archived = False
  attr_list = evt_subscriber_device_proxy.read_attribute("AttributeList").value
  if attr_list is not None:
    for already_archived in attr_list:
      #logging.info("Comparing: " + str(attribute) + " and " + str(already_archived).lower())
      if attribute in str(already_archived).lower():
        is_already_archived = True
        #logging.info("is_already_archived: True")
        break

  if not is_already_archived:
    # wait for the attribute to be up and running for configuring it. 
    #logging.info("Adding attribute not archived....")
    max_retries = 10
    sleep_time = 30
    for x in range(0, max_retries):
        try:
          att = AttributeProxy(attribute)
          att.read()
          #logging.info("Attribute online value=" + str(att.read()))
          break
        except DevFailed as df:
          if(x == (max_retries -1)):
            raise df
          logging.info("DevFailed exception: " + str(df.args[0].reason) + ". Sleeping for " + str(sleep_time) + "ss")
          sleep(sleep_time)
  
    conf_manager_proxy.write_attribute("SetAttributeName", attribute)
    conf_manager_proxy.write_attribute("SetArchiver", evt_subscriber_device_fqdn)
    conf_manager_proxy.write_attribute("SetStrategy", "ALWAYS")
    conf_manager_proxy.write_attribute("SetPollingPeriod", 1000)
    conf_manager_proxy.write_attribute("SetPeriodEvent", 3000)
    conf_manager_proxy.AttributeAdd()
    
  evt_subscriber_device_proxy.Start()
  sleep(3) # the polling
  result_config_manager = conf_manager_proxy.AttributeStatus(attribute)
  result_evt_subscriber = evt_subscriber_device_proxy.AttributeStatus(attribute)
  
  assert "Archiving          : Started" in result_config_manager
  assert "Archiving          : Started" in result_evt_subscriber

  conf_manager_proxy.AttributeRemove(attribute)

@pytest.mark.archiver
def test_configure_attribute():
  attribute = "sys/tg_test/1/double_scalar"
  
  sleep_time = 20
  max_retries = 10
  for x in range(0, max_retries):
    try:
      ApiUtil.cleanup()
      configure_attribute(attribute)
      break
    except:
      logging.info("configure_attribute exception: " + str(sys.exc_info()))
      if(x == (max_retries - 1)):
        raise df
    
    try:
      deviceAdm = DeviceProxy("dserver/hdbppcm-srv/01")
      deviceAdm.RestartServer()
    except:
      logging.info("reset_conf_manager exception: " + str(sys.exc_info()[0]))
    
    sleep(sleep_time)

@pytest.mark.archiver
def test_archiving_started():
  evt_subscriber_device_fqdn = "archiving/hdbpp/eventsubscriber01"
  evt_subscriber_device_proxy = DeviceProxy(evt_subscriber_device_fqdn)

  attribute = "mid_d0001/elt/master/WindSpeed"
  
  result_evt_subscriber = evt_subscriber_device_proxy.AttributeStatus(attribute)
  
  assert "Archiving          : Started" in result_evt_subscriber

