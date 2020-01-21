.. |CI Pipeline| image:: _static/img/ci_pipeline.png 
    :alt: SKAMPI Gitlab CI pipeline
.. |Infra Testware| image:: _static/img/infra_testware.png 
    :alt: Testware architecture and conceptual view

Testing SKAMPI 
==============
The SKA MPI codebase ultimately holds all the information required to deploy and configure the complete prototype.
This information is encapsulated as a collection of `Helm <https://helm.sh/>`_ charts, Makefiles and any other
scripts, components to support its test and deployment.

This page outlines the various categories and approaches one can employ to test various aspects of SKA MPI prototype
that can be implemented in this repository.

Testing Infrastructure as Code
------------------------------
There is a substantial amount of infrastructure and its constituent parts (e.g. Kubernetes resources and their
configuration) that forms part of The Telescope. This configuration is orthogonal to the functionality of the
software components that are deployed, but changes to them can result in faults in deployment and operation of 
the system.

Testing at the appropriate level will ensure faster feedback of changes, reducing frustration for everyone and
ultimately improve the quality of the system. **Troubleshooting faults in a distributed system caused by
a typo in configuration is no fun!**

To support testing, various different jobs are executed as part of the SKAMPI build pipeline and some 
`testware <https://en.wikipedia.org/wiki/Testware>`_ has been developed to aid in testing.


Pipeline Stages for Testing
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The stages of the pipeline related to testing are outlined below:

+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|      Stage      |                                                                                          Description                                                                                          |
+=================+===============================================================================================================================================================================================+
| Static_analysis | Tests aspects of charts that do not require their deployment, e.g. linting                                                                                                                    |
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Unit_test       | A *unit* in this context is a Helm chart. Tests here might deploy them to an `ephemeral test environment <https://pipelinedriven.org/article/ephemeral-environment-why-what-how-and-where>`_. |
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Test            | Tests to be executed in-cluster alongside the fully deployed SKAMPI prototype.                                                                                                                |
+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**SKAMPI Gitlab CI Pipeline** (as of January 2020):
|CI Pipeline|

Python Testware
^^^^^^^^^^^^^^^

Some components have been developed to assist in testing the Helm charts using Python. They are intended to be 
used with `pytest <http://pytest.org/>`_ as a test runner and there are currently two jobs in the pipeline that 
are configured to executed them, filtered based on `pytest markers <https://docs.pytest.org/en/latest/example/markers.html>`_: 

- *helm-template-pytest* runs as part of the *Static_analysis* stage in the pipeline and is intended to execute tests that do not require resources to be deployed in a cluster. Such tests are marked with `no_deploy`.

- *chart-pytest* runs as part of the *Unit_test* stage and will execute tests marked with the ``chart_deploy`` marker. A unit in this case is a helm chart that will be deployed and tested.


|Infra Testware|