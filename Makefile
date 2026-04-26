NPM_CACHE ?= /tmp/armwrestling-npm-cache

.PHONY: app-data dev build typecheck smoke validate npm-install

app-data:
	.venv/bin/python scripts/build_app_bundle.py

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

validate: app-data typecheck build smoke
	.venv/bin/python -m py_compile scripts/*.py
	.venv/bin/ruff check scripts
