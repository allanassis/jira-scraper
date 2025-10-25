.PHONY: install test lint format clean demo help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package and dependencies
	python -m venv jira_scraper_env && source jira_scraper_env/bin/activate && pip install -e .

unit-test:  ## Run tests
	pytest tests/ -v --ignore=tests/test_e2e_cli.py

e2e-test:  ## Run tests
	pytest tests/test_e2e_cli.py -v

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=jira_scraper --cov-report=html --ignore=tests/test_e2e_cli.py

lint:  ## Run linting
	black --check jira_scraper tests
	isort --check-only jira_scraper tests
	mypy jira_scraper

format:  ## Format code
	black jira_scraper tests
	isort jira_scraper tests

demo:  ## Run demo scraper
	python demo.py

scrape:  ## Run full scraper with default settings
	python -m jira_scraper.cli

scrape-small:  ## Run scraper with conservative settings
	python -m jira_scraper.cli -c 2 -r 2.0 -p KAFKA

clean:  ## Clean up generated files
	rm -rf output/ demo_output/ .pytest_cache/ htmlcov/ .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
