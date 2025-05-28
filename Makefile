PYTHON = python3
PIP = pip3
PYTEST = pytest
TEST_PATH = tests/
SRC_PATH = app/

GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m 

.PHONY: help install-test-deps test test-unit test-integration test-e2e test-coverage test-fast test-slow test-auth test-books test-files clean-test lint-test format-test test-watch test-parallel test-report

help:
	@echo "$(GREEN)Доступні команди для тестування:$(NC)"
	@echo ""
	@echo "$(YELLOW)Встановлення залежностей:$(NC)"
	@echo "  install-test-deps     Встановити залежності для тестування"
	@echo ""
	@echo "$(YELLOW)Запуск тестів:$(NC)"
	@echo "  test                  Запустити всі тести"
	@echo "  test-unit            Запустити юніт-тести"
	@echo "  test-integration     Запустити інтеграційні тести"
	@echo "  test-e2e             Запустити end-to-end тести"
	@echo "  test-coverage        Запустити тести з покриттям коду"
	@echo "  test-fast            Запустити швидкі тести (без повільних)"
	@echo "  test-slow            Запустити повільні тести"
	@echo ""
	@echo "$(YELLOW)Тести за категоріями:$(NC)"
	@echo "  test-auth            Тести авторизації"
	@echo "  test-books           Тести книг"
	@echo "  test-files           Тести файлів"
	@echo "  test-api             Тести API"
	@echo "  test-services        Тести сервісів"
	@echo "  test-models          Тести моделей"
	@echo ""
	@echo "$(YELLOW)Додаткові команди:$(NC)"
	@echo "  test-watch           Запустити тести в режимі спостереження"
	@echo "  test-parallel        Запустити тести паралельно"
	@echo "  test-report          Згенерувати детальний звіт тестування"
	@echo "  lint-test            Перевірити код тестів лінтером"
	@echo "  format-test          Відформатувати код тестів"
	@echo "  clean-test           Очистити артефакти тестування"

install-test-deps:
	@echo "$(GREEN)Встановлення залежностей для тестування...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Залежності встановлено успішно!$(NC)"

test:
	@echo "$(GREEN)Запуск всіх тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -v

test-unit:
	@echo "$(GREEN)Запуск юніт-тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m unit -v

test-integration:
	@echo "$(GREEN)Запуск інтеграційних тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m integration -v

test-e2e:
	@echo "$(GREEN)Запуск end-to-end тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m e2e -v

test-coverage:
	@echo "$(GREEN)Запуск тестів з аналізом покриття коду...$(NC)"
	$(PYTEST) $(TEST_PATH) --cov=$(SRC_PATH) --cov-report=html --cov-report=term-missing --cov-fail-under=80
	@echo "$(YELLOW)Звіт покриття збережено в htmlcov/index.html$(NC)"

test-fast:
	@echo "$(GREEN)Запуск швидких тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m "not slow" -v

test-slow:
	@echo "$(GREEN)Запуск повільних тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m slow -v

test-auth:
	@echo "$(GREEN)Запуск тестів авторизації...$(NC)"
	$(PYTEST) $(TEST_PATH) -m auth -v

test-books:
	@echo "$(GREEN)Запуск тестів книг...$(NC)"
	$(PYTEST) $(TEST_PATH) -m books -v

test-files:
	@echo "$(GREEN)Запуск тестів файлів...$(NC)"
	$(PYTEST) $(TEST_PATH) -m files -v

test-api:
	@echo "$(GREEN)Запуск тестів API...$(NC)"
	$(PYTEST) $(TEST_PATH)/test_api/ -v

test-services:
	@echo "$(GREEN)Запуск тестів сервісів...$(NC)"
	$(PYTEST) $(TEST_PATH)/test_services/ -v

test-models:
	@echo "$(GREEN)Запуск тестів моделей...$(NC)"
	$(PYTEST) $(TEST_PATH)/test_models/ -v

test-utils:
	@echo "$(GREEN)Запуск тестів утиліт...$(NC)"
	$(PYTEST) $(TEST_PATH)/test_utils/ -v

test-watch:
	@echo "$(GREEN)Запуск тестів в режимі спостереження...$(NC)"
	@echo "$(YELLOW)Тести будуть перезапускатися при зміні файлів$(NC)"
	$(PYTEST) $(TEST_PATH) -f -v

test-parallel:
	@echo "$(GREEN)Запуск тестів паралельно...$(NC)"
	$(PYTEST) $(TEST_PATH) -n auto -v

test-report:
	@echo "$(GREEN)Генерація детального звіту тестування...$(NC)"
	$(PYTEST) $(TEST_PATH) --html=test-report.html --self-contained-html --cov=$(SRC_PATH) --cov-report=html
	@echo "$(YELLOW)Звіт збережено в test-report.html$(NC)"

test-debug:
	@echo "$(GREEN)Запуск тестів в режимі дебагу...$(NC)"
	$(PYTEST) $(TEST_PATH) -v -s --tb=long --pdb-trace

test-failed:
	@echo "$(GREEN)Перезапуск тільки невдалих тестів...$(NC)"
	$(PYTEST) --lf -v

test-new:
	@echo "$(GREEN)Запуск тільки нових або змінених тестів...$(NC)"
	$(PYTEST) --ff -v

test-quiet:
	@echo "$(GREEN)Запуск тестів (тихий режим)...$(NC)"
	$(PYTEST) $(TEST_PATH) -q

test-verbose:
	@echo "$(GREEN)Запуск тестів (детальний режим)...$(NC)"
	$(PYTEST) $(TEST_PATH) -vv

test-summary:
	@echo "$(GREEN)Запуск тестів з коротким підсумком...$(NC)"
	$(PYTEST) $(TEST_PATH) --tb=short -q

lint-test:
	@echo "$(GREEN)Перевірка коду тестів лінтером...$(NC)"
	flake8 $(TEST_PATH) --max-line-length=100
	pylint $(TEST_PATH) || true

format-test:
	@echo "$(GREEN)Форматування коду тестів...$(NC)"
	black $(TEST_PATH) --line-length=100
	isort $(TEST_PATH)

clean-test:
	@echo "$(GREEN)Очищення артефактів тестування...$(NC)"
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf test-report.html
	rm -rf test.db
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Артефакти очищено!$(NC)"

test-all: clean-test test-coverage
	@echo "$(GREEN)Повне тестування завершено!$(NC)"

test-ci:
	@echo "$(GREEN)Запуск тестів для CI/CD...$(NC)"
	$(PYTEST) $(TEST_PATH) --cov=$(SRC_PATH) --cov-report=xml --cov-report=term --junitxml=test-results.xml -v

test-performance:
	@echo "$(GREEN)Запуск тестів продуктивності...$(NC)"
	$(PYTEST) $(TEST_PATH) -m performance --benchmark-only -v

test-security:
	@echo "$(GREEN)Запуск тестів безпеки...$(NC)"
	$(PYTEST) $(TEST_PATH) -m security -v

create-test:
	@read -p "Назва тестового модуля (без test_ і .py): " name; \
	mkdir -p $(TEST_PATH)/test_$name; \
	echo "import pytest\n\n\nclass Test$name:\n    \"\"\"Тести для $name\"\"\"\n    \n    def test_example(self):\n        \"\"\"Приклад тесту\"\"\"\n        assert True" > $(TEST_PATH)/test_$name/test_$name.py; \
	echo "$(GREEN)Створено $(TEST_PATH)/test_$name/test_$name.py$(NC)"

analyze-tests:
	@echo "$(GREEN)Аналіз структури тестів...$(NC)"
	@echo "$(YELLOW)Загальна кількість тестових файлів:$(NC)"
	@find $(TEST_PATH) -name "test_*.py" | wc -l
	@echo "$(YELLOW)Кількість тестових функцій:$(NC)"
	@grep -r "def test_" $(TEST_PATH) | wc -l
	@echo "$(YELLOW)Розподіл тестів за маркерами:$(NC)"
	@grep -r "@pytest.mark" $(TEST_PATH) | cut -d: -f2 | sort | uniq -c | sort -nr

validate-tests:
	@echo "$(GREEN)Валідація структури тестів...$(NC)"
	@$(PYTEST) --collect-only -q $(TEST_PATH) > /dev/null && echo "$(GREEN)Структура тестів коректна$(NC)" || echo "$(RED)Помилки в структурі тестів$(NC)"

update-snapshots:
	@echo "$(GREEN)Оновлення снепшотів тестів...$(NC)"
	$(PYTEST) $(TEST_PATH) --snapshot-update

test-file:
	@read -p "Шлях до тестового файлу: " filepath; \
	$(PYTEST) $filepath -v

test-class:
	@read -p "Шлях до файлу::Назва класу: " target; \
	$(PYTEST) $target -v

test-function:
	@read -p "Шлях до файлу::назва_функції: " target; \
	$(PYTEST) $target -v

show-fixtures:
	@echo "$(GREEN)Доступні фікстури:$(NC)"
	$(PYTEST) --fixtures -q

show-markers:
	@echo "$(GREEN)Доступні маркери:$(NC)"
	$(PYTEST) --markers

test-env:
	@echo "$(GREEN)Інформація про тестове середовище:$(NC)"
	@echo "Python version: $(python --version)"
	@echo "Pytest version: $(pytest --version)"
	@echo "Working directory: $(pwd)"
	@echo "Test path: $(TEST_PATH)"
	@echo "Source path: $(SRC_PATH)"