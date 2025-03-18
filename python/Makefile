wheel:
	python3 setup.py sdist bdist_wheel

CUR_VERSION = $(shell python -c "from bbqr.version import __version__; print(__version__)")

TARGETS = dist/bbqr-$(CUR_VERSION).tar.gz \
	dist/bbqr-$(CUR_VERSION)-py3-none-any.whl

$(TARGETS) release: wheel
	git add $(TARGETS)
	git tag -am v$(CUR_VERSION) v$(CUR_VERSION)
	twine upload $(TARGETS)

init:
	pip install -r requirements.txt

test:
	py.test tests -x

.PHONY: init test wheel

