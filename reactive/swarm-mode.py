from charms.docker import DockerOpts
from charms.docker import Compose

from charms.leadership import leader_set
from charms.leadership import leader_get

from charms.reactive import remove_state
from charms.reactive import set_state
from charms.reactive import when
from charms.reactive import when_any
from charms.reactive import when_not
from charms.reactive import set_flag

from charmhelpers.core.hookenv import is_leader
from charmhelpers.core.hookenv import log
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.hookenv import unit_get
from charmhelpers.core.hookenv import open_port
from charmhelpers.core.hookenv import unit_private_ip
from charmhelpers.core import unitdata
from charmhelpers.core.host import service_restart
from charmhelpers.core.templating import render

from os import getenv
from os import makedirs
from os import path
from os import remove

from shlex import split
from shutil import copyfile

from tlslib import client_cert
from tlslib import client_key
from tlslib import ca

import subprocess
import socket
import charms.leadership  # noqa

# swarm mode commands
SWARM_PORT = '2377'
SWARM_INIT = ['docker','swarm','init']
SWARM_JOIN = ['docker','swarm','join','--token']
SWARM_TOKEN = ['docker','swarm','join-token','worker','-q']

@when('docker.available')
@when_not('swarm-mode.available', 'leadership.is_leader')
def swarm_init():
    token = leader_get('cluster-worker-token')
    ip = leader_get('cluster-leader-ip')
    cmd = SWARM_JOIN[:]
    cmd.append(token)
    cmd.append(ip + ':' + SWARM_PORT)
    log(str(cmd),'DEBUG')
    try:
        output = subprocess.check_output(cmd)
        log(str(output),'DEBUG')
        set_flag('swarm-mode.available')
    except Exception as e:
        log(str(e), 'ERROR')
        status_set('blocked', 'swarm join error')

### add token activation in this section
@when('leadership.is_leader')
@when('docker.available')
@when_not('swarm-mode.available')
# activate swarm for leader node
def swarm_join():
    try:
        output = subprocess.check_output(SWARM_INIT)
        token = subprocess.check_output(SWARM_TOKEN).decode('utf-8').strip()
        log(str(output),'DEBUG')
        log(str(token),'DEBUG')
        leader_set({
            'cluster-worker-token': token,
            'cluster-leader-ip': unit_private_ip()
        })
        set_flag('swarm-mode.available')
    except Exception as e:
        log(str(e), 'ERROR')
        status_set('blocked', 'swarm init error')

@when('leadership.is_leader')
@when('swarm-mode.available')
def swarm_leader_messaging():
    status_set('active', 'Swarm leader running')


@when_not('leadership.is_leader')
@when('swarm-mode.available')
def swarm_follower_messaging():
    status_set('active', 'Swarm follower')

@when('easyrsa installed')
@when_not('swarm-mode.tls.opensslconfig.modified')
def inject_swarm_tls_template():
    """
    layer-tls installs a default OpenSSL Configuration that is incompatibile
    with how swarm expects TLS keys to be generated. We will append what
    we need to the x509-type, and poke layer-tls to regenerate.
    """

    status_set('maintenance', 'Reconfiguring SSL PKI configuration')

    log('Updating EasyRSA3 OpenSSL Config')
    openssl_config = 'easy-rsa/easyrsa3/x509-types/server'

    with open(openssl_config, 'r') as f:
        existing_template = f.readlines()

    # use list comprehension to enable clients,server usage for certificates
    # with the docker/swarm daemons.
    xtype = [w.replace('serverAuth', 'serverAuth, clientAuth') for w in existing_template]  # noqa
    with open(openssl_config, 'w+') as f:
        f.writelines(xtype)

    set_state('swarm-mode.tls.opensslconfig.modified')
    set_state('easyrsa configured')


@when('tls.server.certificate available')
def enable_client_tls():
    """
    Copy the TLS certificates in place and generate mount points for the swarm
    manager to mount the certs. This enables client-side TLS security on the
    TCP service.
    """
    if not path.exists('/etc/docker'):
        makedirs('/etc/docker')

    kv = unitdata.kv()
    cert = kv.get('tls.server.certificate')
    with open('/etc/docker/server.pem', 'w+') as f:
        f.write(cert)
    with open('/etc/docker/ca.pem', 'w+') as f:
        f.write(leader_get('certificate_authority'))

    # schenanigans
    keypath = 'easy-rsa/easyrsa3/pki/private/{}.key'
    server = getenv('JUJU_UNIT_NAME').replace('/', '_')
    if path.exists(keypath.format(server)):
        copyfile(keypath.format(server), '/etc/docker/server-key.pem')
    else:
        copyfile(keypath.format(unit_get('public-address')),
                 '/etc/docker/server-key.pem')

    opts = DockerOpts()
    config_dir = '/etc/docker'
    cert_path = '{}/server.pem'.format(config_dir)
    ca_path = '{}/ca.pem'.format(config_dir)
    key_path = '{}/server-key.pem'.format(config_dir)
    opts.add('tlscert', cert_path)
    opts.add('tlscacert', ca_path)
    opts.add('tlskey', key_path)
    opts.add('tlsverify', None)
    private_address = unit_private_ip()
    opts.add('host', 'tcp://{}:2376'.format(private_address))
    opts.add('host', 'unix:///var/run/docker.sock')
    render('docker.defaults', '/etc/default/docker', {'opts': opts.to_s()})
    open_port(2376)

# @when('leadership.is_leader')
# def open_swarm_manager_port():
#     open_port(3376)

@when('leadership.is_leader')
@when('tls.client.certificate available')
@when_not('leadership.set.client_cert', 'leadership.set.client_key')
def prepare_default_client_credentials():
    """ Generate a downloadable package for clients to use to speak to the
    swarm cluster. """

    # Leverage TLSLib to copy the default cert from PKI
    client_cert(None, './swarm_credentials/cert.pem')
    client_key(None, './swarm_credentials/key.pem')
    ca(None, './swarm_credentials/ca.pem')

    with open('swarm_credentials/key.pem', 'r') as fp:
        key_contents = fp.read()
    with open('swarm_credentials/cert.pem', 'r') as fp:
        crt_contents = fp.read()

    leader_set({'client_cert': crt_contents,
                'client_key': key_contents})


@when_any('leadership.changed.client_cert', 'leadership.changed.client_key')
@when_not('client.credentials.placed')
def prepare_end_user_package():
    """ Prepare the tarball package for clients to use to connet to the
        swarm cluster using the default client credentials. """

    # If we are a follower, we dont have keys and need to fetch them
    # from leader-data, which triggered `leadership.set.client_cert`
    # So it better be there!
    if not path.exists('swarm_credentials'):
        makedirs('swarm_credentials')
        with open('swarm_credentials/key.pem', 'w+') as fp:
            fp.write(leader_get('client_key'))
        with open('swarm_credentials/cert.pem', 'w+') as fp:
            fp.write(leader_get('client_cert'))
        with open('swarm_credentials/ca.pem', 'w+') as fp:
            fp.write(leader_get('certificate_authority'))

    # Render the client package script
    template_vars = {'public_address': unit_get('public-address')}
    render('enable.sh', './swarm_credentials/enable.sh', template_vars)

    # clear out any stale credentials package
    if path.exists('swarm_credentials.tar'):
        remove('swarm_credentials.tar')

    cmd = 'tar cvfz swarm_credentials.tar.gz swarm_credentials'
    subprocess.check_call(split(cmd))
    copyfile('swarm_credentials.tar.gz',
             '/home/ubuntu/swarm_credentials.tar.gz')
    set_state('client.credentials.placed')


    
