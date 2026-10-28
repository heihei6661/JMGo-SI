.PHONY: install test lint demo clean

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m unittest discover -s tests -v

lint:
	python3 -m ruff check .

demo:
	python3 -m jmgo_cognition.cli "把桌上的杯子拿过来"

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
