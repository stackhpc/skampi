"""
Example script for resource allocation
"""
import logging
import os
import errno

from oet.domain import SubArray

LOG = logging.getLogger(__name__)
FORMAT = '%(asctime)-15s %(message)s'

logging.basicConfig(level=logging.INFO, format=FORMAT)


def main(configuration, scan_duration, subarray_id=1):
    """
    Configure a sub-array and perform the scan.

    :param configuration: name of configuration file
    :param scan_duration: scan duration in seconds
    :param subarray_id: numeric subarray ID
    :return:
    """
    LOG.info(f'Running observe script in OS process {os.getpid()}')
    LOG.info(f'Called with main(configuration={configuration}, scan_duration={scan_duration}, subarray_id={subarray_id})')

    if not os.path.isfile(configuration):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), configuration)

    subarray = SubArray(subarray_id)
    LOG.info('Configure subarray')
    subarray.configure_from_file(configuration)

    LOG.info('Perform scan')
    subarray.scan(float(scan_duration))

    LOG.info('End scheduling block')
    subarray.end_sb()

    LOG.info('Observation script complete')
