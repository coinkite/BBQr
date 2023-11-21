
init:
	pip install -r requirements.txt

test:
	py.test tests -x

.PHONY: init test

