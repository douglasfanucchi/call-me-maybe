MYPY_FLAGS=--warn-return-any\
			--warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs\
			--check-untyped-defs --exclude .venv
FUNCTIONS_DEFINITION=data/input/functions_definition.json
INPUT=data/input/function_calling_tests.json
OUTPUT=data/output/function_calls.json

install:
	@uv sync

run: install
	@uv run python3 -m src\
		--functions_definition $(FUNCTIONS_DEFINITION)\
		--input $(INPUT)\
		--output $(OUTPUT)

debug: install
	@uv run python3 -m pdb src/__main__.py

clean:
	@find . \( -name "*__pycache__*" -o -name "*.mypy_cache*" \) -exec rm -rf {} +;

lint:
	@flake8 --exclude .venv
	@mypy $(MYPY_FLAGS) .

lint-strict:
	@flake8
	@mypy $(MYPY_FLAGS) --strict .
