PYTHON ?= python3.12
VENV ?= .venv
PYTHON_VENV ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
UVICORN ?= $(VENV)/bin/uvicorn

.PHONY: help venv venv-recreate install run clean

help:
	@echo "Targets:"
	@echo "  make venv PYTHON=python3.12  Create venv with a specific interpreter"
	@echo "  make venv-recreate PYTHON=python3.12  Recreate venv with interpreter"
	@echo "  make venv     Create virtualenv"
	@echo "  make install  Install dependencies"
	@echo "  make run      Run FastAPI server"
	@echo "  make clean    Remove venv and db"

venv:
	@if [ -x "$(PYTHON_VENV)" ]; then \
		venv_py=$$($(PYTHON_VENV) -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")'); \
		req_py=$$($(PYTHON) -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")'); \
		if [ "$$venv_py" != "$$req_py" ]; then \
			echo "Recreating venv (found $$venv_py, want $$req_py)"; \
			rm -rf $(VENV); \
		fi; \
	fi
	$(PYTHON) -m venv $(VENV)

venv-recreate:
	rm -rf $(VENV)
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

run: install
	$(UVICORN) backend.main:app --reload

clean:
	rm -rf $(VENV) data
