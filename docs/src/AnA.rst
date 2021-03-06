A&A
===
In this section there are some instruction on how it is possible to setup the A&A (Authentication and Authorization) in k8s/minikube. 

Static File Authentication
--------------------------

To enable authentication with `static file <https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-password-file>`_ in a minikube environment, start it with the following command (consult the `kubernetes documentation <https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-password-file>`_ for the formatting of `users.csv`):

.. code-block:: bash

    sudo -E minikube start --vm-driver=none \
        --extra-config=kubelet.resolv-conf=/var/run/systemd/resolve/resolv.conf \
        --extra-config=apiserver.basic-auth-file=/var/lib/minikube/certs/users.csv

OpenID Connect Tokens Authentication
------------------------------------

To enable authentication with `OpenID Connect Tokens <https://kubernetes.io/docs/reference/access-authn-authz/authentication/#openid-connect-tokens)>`_ in a minikube environment, for instance with Gitlab, start it with the following command:

.. code-block:: bash

    export CLIENT_ID=f84585f68a80c8d6292ec13bb691a19889d80635ffae4e821285c9d3c1980343
    sudo -E minikube start --vm-driver=none \
        --extra-config=kubelet.resolv-conf=/var/run/systemd/resolve/resolv.conf \
        --extra-config=apiserver.authorization-mode=RBAC \
        --extra-config=apiserver.oidc-issuer-url=https://gitlab.com \
        --extra-config=apiserver.oidc-username-claim=sub  \
        --extra-config=apiserver.oidc-client-id=$CLIENT_ID

The parameter ``apiserver.oidc-client-id`` must correspond to the `application id <https://gitlab.com/profile/applications>`_ created in gitlab.

Once the minikube is started, to configure the kubectl tool, it is possible to use `gangway <https://github.com/heptiolabs/gangway>`_. To install it:

.. code-block:: bash

    export from_gitlab_applicationid=f84585f68a80c8d6292ec13bb691a19889d80635ffae4e821285c9d3c1980343
    export from_gitlab_applicationsecret=432899cbbb1f0d4dcbef60d38013e5cbfc5b0c6e60d3356207e811508a6ddebc
    make gangway CLIENT_ID=$from_gitlab_applicationid \
        CLIENT_SECRET=$from_gitlab_applicationsecret \
        INGRESS_HOST=integration.engageska-portugal.pt \
        API_SERVER_PORT=8443 \
        API_SERVER_IP=xxx.xxx.xxx.xxx 

The result will be a new ingress at the link `gangway.integration.engageska-portugal.pt`. Remember to modify the file `/etc/hosts` adding the following lines:

.. code-block:: bash

    xxx.xxx.xxx.xxx 	integration.engageska-portugal.pt
    xxx.xxx.xxx.xxx     gangway.integration.engageska-portugal.pt


*The clusters available in skampi are enabled with the OpenID Connect Tokens Authentication.*

Authorization
=============

There are two possibilities for authorization in k8s: the first one is called RBAC (Role-based access control) and the second one is called ABAC (Attribute-based access control).

RBAC
----

`RBAC <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>`_ allows authorization based on the roles of individual users within an enterprise. A role contains a set of rules which define
* an API group (all the k8s api is divided into a set of groups),
* a set of resources like pod, deployment and so on,
* a set of verbs like get, list and so on 

Each role is related to the users with a resource called RoleBinding. The file `roles.yaml` shows an example of Role and RoleBinding which make the user "matteo" able to work (do anything) on the "integration" namespace.

*The clusters available in skampi are enabled with RBAC.*

ABAC
----

`ABAC <https://kubernetes.io/docs/reference/access-authn-authz/abac/>`_ allows authorization according to a set of policies which combine attributes together. The authorization policy is specified into a file with format one JSON object per line. Each line is a policy object containing which specify versioning information and specification, for example:

.. code-block:: JSON

    {"apiVersion": "abac.authorization.kubernetes.io/v1beta1", 
      "kind": "Policy", 
      "spec": {
        "user": "matteo", 
        "namespace": "integration", 
        "resource": "", 
        "apiGroup": ""}}

KUBECONFIG
==========

The command `kubectl config view` shows the current configuration of the running minikube instance. In order to reproduce the PoC of this folder it is necessary to modify it adding the context for the user to access the local cluster (the file `kubeconfig` shows how it has been modified). 
More information can be found `here <https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/>`_