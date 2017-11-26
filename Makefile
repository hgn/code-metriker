MKFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJ_SRC_PATH := $(notdir $(patsubst %/,%,$(dir $(MKFILE_PATH))))
ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
EXEC_DIR := /usr/share/code-metriker
CONF_DIR := /etc/code-metriker


help:
	@echo "install - install distribution to /use/share/code-metriker and systemd unit file"

all:
	help

uninstall:
	@echo "remove runtime data in $(EXEC_DIR)"
	@rm -rf $(EXEC_DIR)
	@if [ -d "$(CONF_DIR)" ] ; \
	then \
		echo "did NOT remove configuration file in $(CONF_DIR) - remove manually if required:" ; \
		echo "e.g. rm -rf $(CONF_DIR)" ; \
	fi
	@echo "uninstallation completed"

install:
	@if [ -d "$(EXEC_DIR)" ] ; \
	then \
		echo "$(EXEC_DIR) present, remove first" ; \
		echo "e.g. \"make uninstall\"" ; \
		exit 1 ; \
	fi
	@if [ -d "$(CONF_DIR)" ] ; \
	then \
		echo "$(CONF_DIR) present, did not overwrite convfiguration" ; \
	else \
		echo "create dir $(CONF_DIR)" ; \
		mkdir -p $(CONF_DIR) ; \
		cp $(ROOT_DIR)/conf/code-metriker.conf $(CONF_DIR)/ ; \
	fi
	mkdir -p $(EXEC_DIR)
	cp -r $(ROOT_DIR)/* $(EXEC_DIR)
	cp conf/code-metriker.service /lib/systemd/system/
	chmod 644 /lib/systemd/system/code-metriker.service
	@echo "now call systemctl daemon-reload"
	@echo ".. enable service via: systemctl enable code-metriker"
	@echo ".. start service via: systemctl start code-metriker"
	@echo ".. status via: systemctl status code-metriker"
	@echo ".. logging via: journalctl -u code-metriker"
	@echo ""
	@echo "Don't forget to install required python modules (for root): \"sudo -H pip3 install -r requirements.txt\""
	@echo "and \"sudo apt-get install python3-pip\""

ctags:
	ctags -R .
