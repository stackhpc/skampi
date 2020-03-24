Feature: Generate a scan ID
    # Generate uinique scan IDs
    # The scan ID format shall be per https://gitlab.com/ska-telescope/skuid/-/blob/master/docs/src/uid_format.rst

Scenario: OET requests a scan ID
    Given I am accessing the console interface for the OET
    Given Sub-array is resourced
    When I call the configure scan execution instruction
    Then Sub-array is in READY state
    Then Sub-array reports scan ID
