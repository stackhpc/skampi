#!/bin/bash

set -e -o pipefail
echo "pipefail set"
sleep 20s 
x=$(kubectl get pods -n integration --field-selector=status.phase=Running | wc -l)
echo "$x"
for i in 1 2 3 4 5 6 7 8 9
do
	if [ $x = "21" ]; then
		echo "20 pods running"
		exit 
	else
		sleep 20s
		echo "waiting ...($i * 20)s"
echo "not all pods are running"
exit 1
fi
