.PHONY: check lint type test cov serve refresh

check: lint type test

lint:
	ruff check compass tests
	ruff format --check compass tests

type:
	mypy compass

test:
	pytest -q

cov:
	pytest --cov=compass --cov-report=term-missing

serve:
	compass serve

refresh:
	python -m compass.data.refresh
