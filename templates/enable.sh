#!/bin/bash

export DOCKER_TLS_VERIFY=1
export DOCKER_HOST=tcp://{{ public_address }}:2376
export DOCKER_CERT_PATH=$(pwd)
