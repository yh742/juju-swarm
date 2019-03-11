#!/bin/bash

sudo charm build .
mkdir ~/charms/builds/swarm-mode
sudo cp -r /tmp/charm-builds/swarm-mode ~/charms/builds/swarm-mode
cd ~/charms/builds/swarm-mode
# python3 tests/10-deploy
