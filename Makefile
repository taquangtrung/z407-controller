CONDA_ENV ?= z407
PY_VERSION ?= 3.12
BIN_DIR   ?= $(HOME)/.local/bin
APPS_DIR  ?= $(HOME)/.local/share/applications
ICON_DIR  ?= $(HOME)/.local/share/icons/hicolor/scalable/apps

# Resolve the env's bin dir lazily so it works before and after creation.
ENV_BIN = $(shell conda env list | awk '$$1 == "$(CONDA_ENV)" {print $$NF}')/bin

.PHONY: dev install uninstall test lint env

# Create the conda env if it does not exist yet.
env:
	@conda env list | awk '{print $$1}' | grep -qx '$(CONDA_ENV)' \
		|| conda create -n $(CONDA_ENV) -c conda-forge --override-channels python=$(PY_VERSION) -y

# Editable install with dev extras into the conda env, then launch the GUI.
dev: env
	$(ENV_BIN)/pip install -e ".[dev]"
	$(ENV_BIN)/z407-gui

# Install into the conda env and link `z407-cli` and `z407-gui` onto PATH.
install: env
	$(ENV_BIN)/pip install --upgrade .
	mkdir -p $(BIN_DIR)
	rm -f $(BIN_DIR)/z407
	ln -sf $(ENV_BIN)/z407-cli $(BIN_DIR)/z407-cli
	ln -sf $(ENV_BIN)/z407-gui $(BIN_DIR)/z407-gui
	mkdir -p $(ICON_DIR) $(APPS_DIR)
	cp src/z407/gui/static/icon.svg $(ICON_DIR)/z407-gui.svg
	printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Z407 Controller' \
		'Comment=Control Logitech Z407 speakers' 'Exec=$(BIN_DIR)/z407-gui' \
		'Icon=z407-gui' 'Categories=AudioVideo;Audio;' 'Terminal=false' \
		> $(APPS_DIR)/z407-gui.desktop
	@echo "Installed z407-cli and z407-gui in $(BIN_DIR) (make sure it is on your PATH)"

uninstall:
	rm -f $(BIN_DIR)/z407-cli $(BIN_DIR)/z407-gui $(APPS_DIR)/z407-gui.desktop $(ICON_DIR)/z407-gui.svg
	$(ENV_BIN)/pip uninstall -y z407-controller

test: env
	$(ENV_BIN)/pytest

lint: env
	$(ENV_BIN)/ruff check src tests
