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
	make install

$(FLAKE8):
	make install

install:
	rm -rf $(VENV) &&\
	python3 -m venv $(VENV) &&\
	source $(VENV)/bin/activate &&\
	python3 -m pip install uv && \
	uv pip install pydantic flake8 mypy

clean:
	@rm -rf $(CACHE_DIRS)

lint: $(MYPY) $(FLAKE8)
	@source $(VENV)/bin/activate &&\
	python3 -m flake8 --exclude $(VENV) . &&\
	python3 -m mypy $(MYPY_FLAGS) .

lint-strict: $(MYPY) $(FLAKE8)
	@source $(VENV)/bin/activate &&\
	python3 -m flake8 --exclude $(VENV) . &&\
	python3 -m mypy $(MYPY_FLAGS) .
