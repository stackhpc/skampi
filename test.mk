.PHONY: template_tests

TEST_NAMESPACE?=
PYTEST_ARGS?=$(if $(CI),--test-namespace=$(TEST_NAMESPACE),)

template_tests:
	rc=0; \
	for chrt in `ls charts/`; do \
	helm unittest -f template_tests/*_test.yaml charts/$$chrt \
		|| rc=2 && continue; \
	done; \
	exit $$rc

template_pytests:
	python3 -m pytest "-m no_deploy $(PYTEST_ARGS)"

chart_pytests:
	python3 -m pytest "-m chart_deploy --use-tiller-plugin $(PYTEST_ARGS)"