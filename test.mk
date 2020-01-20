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

