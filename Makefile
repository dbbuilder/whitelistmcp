.PHONY: help install install-dev install-qa format lint type-check security test coverage clean qa quick-check fix-imports fix-type-hints build docs profile

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)WhitelistMCP - Multi-Cloud Security Management$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(GREEN)Installation:$(NC)"
	@echo "  install         - Install production dependencies"
	@echo "  install-dev     - Install development dependencies"
	@echo "  install-qa      - Install code quality tools"
	@echo "  install-all     - Install everything (dev + qa)"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  format          - Format code with black and isort"
	@echo "  lint            - Run all linters (flake8, pylint, ruff)"
	@echo "  type-check      - Run type checking with mypy"
	@echo "  security        - Run security checks (bandit, safety)"
	@echo "  complexity      - Check code complexity"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  test            - Run all tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  coverage        - Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Fixes:$(NC)"
	@echo "  fix-imports     - Remove unused imports"
	@echo "  fix-type-hints  - Add missing type hints (interactive)"
	@echo "  fix-all         - Fix all auto-fixable issues"
	@echo ""
	@echo "$(GREEN)Workflows:$(NC)"
	@echo "  qa              - Run all quality checks"
	@echo "  quick-check     - Quick checks (format, lint, type)"
	@echo "  pre-commit      - Run pre-commit checks"
	@echo "  check-all       - Run comprehensive analysis"
	@echo ""
	@echo "$(GREEN)Other:$(NC)"
	@echo "  clean           - Clean up temporary files"
	@echo "  build           - Build distribution packages"
	@echo "  docs            - Generate documentation"
	@echo "  profile         - Profile code performance"

# Installation targets
install:
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	pip install -e .

install-dev:
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	pip install -e ".[dev]"

install-qa:
	@echo "$(BLUE)Installing QA tools...$(NC)"
	pip install -e ".[qa]"

install-all: install-dev install-qa
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

# Code formatting
format:
	@echo "$(BLUE)🎨 Formatting code...$(NC)"
	@echo "  Running black..."
	@black whitelistmcp tests --quiet || echo "$(RED)✗ Black formatting failed$(NC)"
	@echo "  Running isort..."
	@isort whitelistmcp tests --quiet || echo "$(RED)✗ Import sorting failed$(NC)"
	@echo "$(GREEN)✓ Code formatted$(NC)"

# Linting
lint:
	@echo "$(BLUE)🔍 Running linters...$(NC)"
	@echo "  Running flake8..."
	@flake8 whitelistmcp --count --statistics --show-source || echo "$(YELLOW)⚠ Flake8 found issues$(NC)"
	@echo "  Running pylint..."
	@pylint whitelistmcp --exit-zero --score=y || true
	@echo "  Running ruff..."
	@ruff check whitelistmcp || echo "$(YELLOW)⚠ Ruff found issues$(NC)"
	@echo "$(GREEN)✓ Linting complete$(NC)"

# Type checking
type-check:
	@echo "$(BLUE)📝 Running type checker...$(NC)"
	@mypy whitelistmcp --show-error-codes --pretty || echo "$(YELLOW)⚠ Type errors found$(NC)"
	@echo "$(GREEN)✓ Type checking complete$(NC)"

# Security checks
security:
	@echo "$(BLUE)🔒 Running security scans...$(NC)"
	@echo "  Running bandit..."
	@bandit -r whitelistmcp -ll --format json -o bandit-report.json || true
	@bandit -r whitelistmcp -ll || echo "$(YELLOW)⚠ Security issues found$(NC)"
	@echo "  Checking dependencies with safety..."
	@safety check --json || echo "$(YELLOW)⚠ Vulnerable dependencies found$(NC)"
	@echo "  Auditing with pip-audit..."
	@pip-audit || echo "$(YELLOW)⚠ Dependency vulnerabilities found$(NC)"
	@echo "$(GREEN)✓ Security scan complete$(NC)"

# Code complexity
complexity:
	@echo "$(BLUE)📊 Checking code complexity...$(NC)"
	@radon cc whitelistmcp -s -a || echo "$(YELLOW)⚠ Complex functions found$(NC)"
	@radon mi whitelistmcp -s || echo "$(YELLOW)⚠ Maintainability issues found$(NC)"
	@echo "$(GREEN)✓ Complexity check complete$(NC)"

# Testing
test:
	@echo "$(BLUE)🧪 Running all tests...$(NC)"
	@pytest tests/ -v || echo "$(RED)✗ Tests failed$(NC)"

test-unit:
	@echo "$(BLUE)🧪 Running unit tests...$(NC)"
	@pytest tests/ -v -m unit || echo "$(RED)✗ Unit tests failed$(NC)"

test-integration:
	@echo "$(BLUE)🧪 Running integration tests...$(NC)"
	@pytest tests/ -v -m integration || echo "$(RED)✗ Integration tests failed$(NC)"

coverage:
	@echo "$(BLUE)📊 Running tests with coverage...$(NC)"
	@pytest tests/ --cov=whitelistmcp --cov-report=html --cov-report=term --cov-report=json
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

# Fix commands
fix-imports:
	@echo "$(BLUE)🔧 Fixing imports...$(NC)"
	@autoflake --in-place --remove-all-unused-imports --recursive whitelistmcp || echo "$(YELLOW)Install autoflake: pip install autoflake$(NC)"
	@isort whitelistmcp tests --quiet
	@echo "$(GREEN)✓ Imports fixed$(NC)"

fix-type-hints:
	@echo "$(BLUE)🔧 Adding type hints...$(NC)"
	@echo "$(YELLOW)Note: This requires manual review$(NC)"
	@monkeytype stub whitelistmcp || echo "$(YELLOW)Install monkeytype: pip install monkeytype$(NC)"

fix-all: fix-imports format
	@echo "$(GREEN)✓ All auto-fixes applied$(NC)"

# Clean up
clean:
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ dist/ build/ *.egg-info
	@rm -f .coverage coverage.json bandit-report.json
	@echo "$(GREEN)✓ Clean complete$(NC)"

# Combined quality checks
qa: clean format lint type-check security complexity
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)✅ All quality checks completed!$(NC)"
	@echo "$(GREEN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

quick-check: format lint type-check
	@echo "$(GREEN)✅ Quick checks completed!$(NC)"

pre-commit:
	@echo "$(BLUE)🎣 Running pre-commit hooks...$(NC)"
	@pre-commit run --all-files || echo "$(YELLOW)⚠ Pre-commit checks failed$(NC)"

# Run the comprehensive checker
check-all:
	@echo "$(BLUE)🚀 Running comprehensive analysis...$(NC)"
	@python check_code_quality.py -v || echo "$(YELLOW)⚠ Quality issues found$(NC)"

# Build and documentation
build: clean
	@echo "$(BLUE)📦 Building distribution packages...$(NC)"
	@python -m build
	@echo "$(GREEN)✓ Build complete$(NC)"

docs:
	@echo "$(BLUE)📚 Generating documentation...$(NC)"
	@sphinx-apidoc -o docs/source whitelistmcp/ || echo "$(YELLOW)Install sphinx: pip install sphinx$(NC)"
	@cd docs && make html || echo "$(YELLOW)Documentation generation failed$(NC)"
	@echo "$(GREEN)✓ Documentation in docs/build/html$(NC)"

profile:
	@echo "$(BLUE)⚡ Profiling performance...$(NC)"
	@python -m cProfile -o profile.stats -s cumulative whitelistmcp/main.py || echo "$(YELLOW)Profiling failed$(NC)"
	@python -c "import pstats; p = pstats.Stats('profile.stats'); p.strip_dirs().sort_stats('cumulative').print_stats(20)"
	@echo "$(GREEN)✓ Profile complete$(NC)"