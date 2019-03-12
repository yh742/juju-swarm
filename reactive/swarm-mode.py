import subprocess
import socket
from charms.reactive import when, when_not, set_flag
from charmhelpers.core.hookenv import is_leader, status_set, leader_set, leader_get, log

SWARM_TOKEN = ['docker','swarm','join-token','worker','-q']

@when('docker.available')
@when_not('swarm-mode.available')
# activate swarm for new nodes
def leader_swarm():
    SWARM_PORT = '2377'
    SWARM_INIT = ['docker','swarm','init']
    SWARM_JOIN = ['docker','swarm','join','--token']
    if is_leader():
        try:
            output = subprocess.check_output(SWARM_INIT)
            token = subprocess.check_output(SWARM_TOKEN).decode('utf-8').strip()
            log(str(output),'DEBUG')
            log(str(token),'DEBUG')
            leader_set({
                'cluster-worker-token': token,
                'cluster-leader-ip': socket.gethostbyname(socket.gethostname())
            })
            status_set('active', 'swarm leader set')
            set_flag('swarm-mode.available')
        except Exception as e:
            log(str(e), 'ERROR')
            status_set('blocked', 'swarm init error')
    else:
        token = leader_get('cluster-worker-token')
        ip = leader_get('cluster-leader-ip')
        cmd = SWARM_JOIN[:]
        cmd.append(token)
        cmd.append(ip + ':' + SWARM_PORT)
        log(str(cmd),'DEBUG')
        try:
            output = subprocess.check_output(cmd)
            log(str(output),'DEBUG')
            status_set('active', 'swarm worker set')
            set_flag('swarm-mode.available')
        except Exception as e:
            log(str(e), 'ERROR')
            status_set('blocked', 'swarm join error')
    
