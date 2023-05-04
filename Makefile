PYTHON := /usr/bin/python3

PROJECTPATH=$(dir $(realpath $(MAKEFILE_LIST)))
ifndef CHARM_BUILD_DIR
	CHARM_BUILD_DIR=${PROJECTPATH}/build
endif
ifndef CHARM_LAYERS_DIR
	CHARM_LAYERS_DIR=${PROJECTPATH}/layers
endif
ifndef CHARM_INTERFACES_DIR
	CHARM_INTERFACES_DIR=${PROJECTPATH}/interfaces
endif
ifdef CONTAINER
	BUILD_ARGS="--destructive-mode"
endif
METADATA_FILE="src/metadata.yaml"
CHARM_NAME=$(shell cat ${PROJECTPATH}/${METADATA_FILE} | grep -E "^name:" | awk '{print $$2}')

help:
	@echo "This project supports the following targets"
	@echo ""
	@echo " make help - show this text"
	@echo " make clean - remove unneeded files"
	@echo " make submodules - make sure that the submodules are up-to-date"
	@echo " make submodules-update - update submodules to latest changes on remote branch"
	@echo " make build - build the charm"
	@echo " make release - run clean, submodules, and build targets"
	@echo " make lint - run flake8 and black --check"
	@echo " make black - run black and reformat files"
	@echo " make proof - run charm proof"
	@echo " make unittests - run the tests defined in the unittest subdirectory"
	@echo " make functional - run the tests defined in the functional subdirectory"
	@echo " make test - run lint, proof, unittests and functional targets"
	@echo ""

clean:
	@echo "Cleaning files"
	@git clean -ffXd -e '!.idea'
	@echo "Cleaning existing build"
	@rm -rf ${CHARM_BUILD_DIR}/${CHARM_NAME}
	@rm -rf ${PROJECTPATH}/${CHARM_NAME}.charm
	@charmcraft clean

submodules:
	# @git submodule update --init --recursive
	@echo "No submodules. Skipping."

submodules-update:
	# @git submodule update --init --recursive --remote --merge
	@echo "No submodules. Skipping."

build: clean
	@echo "Building charm"
	@-git rev-parse --abbrev-ref HEAD > ./src/repo-info
	@charmcraft pack --destructive-mode
	@bash -c ./rename.sh
	@mkdir -p ${CHARM_BUILD_DIR}/${CHARM_NAME}
	@unzip ${PROJECTPATH}/${CHARM_NAME}.charm -d ${CHARM_BUILD_DIR}/${CHARM_NAME}

release: clean build
	@echo "Charm is built at ${CHARM_BUILD_DIR}/${CHARM_NAME}"

lint:
	@echo "Running lint checks"
	@cd src && tox -e lint

black:
	@echo "Reformat files with black"
	@cd src && tox -e black

proof: build
	@echo "Running charm proof"
	@charm proof ${CHARM_BUILD_DIR}/${CHARM_NAME}

unittests:
	# @cd src && tox -e unit
	@echo "No unit tests. Skipping."

functional: build
	@echo "Executing functional tests in ${CHARM_BUILD_DIR}"
	@cd src && CHARM_LOCATION=${PROJECTPATH} tox -e func

test: lint proof unittests functional
	@echo "Tests completed for charm ${CHARM_NAME}."

# The targets below don't depend on a file
.PHONY: help submodules submodules-update clean build release lint black proof unittests functional test
