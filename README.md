# juju-swarm

Juju swarm mode charm layer 

# Usage

juju deploy ./swarm-mode

# Connect to Docker Daemon

juju scp swarm/0:swarm_credentials.tar .juju scp swarm-mode/0:swarm_credentials.tar . <br />
tar zxf swarm_credentials.tar<br />
cd swarm_credentials<br />
source enable.sh<br />

this downloads the appropraite credentials for accessing the swarm and set the environement variables for accessing the docker daemon on the swarm leader

# Scaling

juju add-unit swarm-mode

# Notes

For docker-compose to work, export the following variable to the environemnt:

export COMPOSE_TLS_VERSION=TLSv1_2
