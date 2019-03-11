from charms.reactive import when, when_not, set_flag
from charmhelpers.core.hookenv import is_leader

@when('docker.available')
def join_swarm():
    if is_leader:
        status_set('maintenance', 'swarm init')
    else:
        status_set('maintenance', 'swarm join')

@when_not('swarm-mode.installed')
def install_swarm_mode():
    # Do your setup here.
    #
    # If your charm has other dependencies before it can install,
    # add those as @when() clauses above., or as additional @when()
    # decorated handlers below
    #
    # See the following for information about reactive charms:
    #
    #  * https://jujucharms.com/docs/devel/developer-getting-started
    #  * https://github.com/juju-solutions/layer-basic#overview
    #
    set_flag('swarm-mode.installed')
