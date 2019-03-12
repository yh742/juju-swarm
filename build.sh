#!/bin/bash

sudo charm build .
# mkdir ~/charms/builds/swarm-mode
# rm -rf ~/charm/builds/swarm-mode/*
#sudo cp -r /tmp/charm-builds/swarm-mode ~/charms/builds/swarm-mode
juju deploy /tmp/charm-builds/swarm-mode/ -n 2
# python3 tests/10-deploy
