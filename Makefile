NPM_CACHE ?= /tmp/armwrestling-npm-cache
PYTHON ?= python3

.PHONY: app-data dev build typecheck smoke stylecheck validate npm-install

app-data:
	$(PYTHON) scripts/build_app_bundle.py

npm-install:
	npm --prefix app ci --cache $(NPM_CACHE)

dev: npm-install app-data
	npm --prefix app run dev

build: npm-install app-data
	npm --prefix app run build

typecheck: npm-install
	npm --prefix app run typecheck

smoke: npm-install app-data
	npm --prefix app run smoke
	SMOKE_VIEWPORT=mobile npm --prefix app run smoke

stylecheck: build
	npm --prefix app run stylecheck

validate: app-data typecheck build stylecheck smoke
	$(PYTHON) -m py_compile scripts/*.py
	.venv/bin/ruff check scripts
