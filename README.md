# juju-swarm

Juju swarm mode charm layer 

# Usage

juju deploy ./swarm-mode

# Connect to Docker Daemon

juju scp swarm/0:swarm_credentials.tar .juju scp swarm/0:swarm_credentials.tar .
tar zxf swarm_credentials.tar
cd swarm_credentials
source enable.sh

this sets the proper credentials for accessing the swarm nodes

# Scaling

juju add-unit swarm-mode
