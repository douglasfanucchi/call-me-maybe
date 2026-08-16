VENV=.venv
DEPENDENCIES_FILE=requirements.txt
CACHE_DIRS:=__pycache__ .mypy_cache
CACHE_DIRS:=$(CACHE_DIRS) $(addprefix */**/, $(CACHE_DIRS))
MYPY=$(VENV)/bin/mypy
FLAKE8=$(VENV)/bin/flake8
MYPY_FLAGS=--warn-return-any --warn-unused-ignores \
			--ignore-missing-imports --disallow-untyped-defs \
			--check-untyped-defs

lint-strict: MYPY_FLAGS:=$(MYPY_FLAGS) --strict

$(MYPY):
	uv sync

$(FLAKE8):
	uv sync

install:
	rm -rf $(VENV)
	uv venv
	uv sync --no-dev

clean:
	@rm -rf $(CACHE_DIRS)

lint: $(MYPY) $(FLAKE8)
	@uv run flake8 --exclude $(VENV) .
	@uv run mypy $(MYPY_FLAGS) .

lint-strict: $(MYPY) $(FLAKE8)
	@uv run flake8 --exclude $(VENV) .
	@uv run mypy $(MYPY_FLAGS) .
