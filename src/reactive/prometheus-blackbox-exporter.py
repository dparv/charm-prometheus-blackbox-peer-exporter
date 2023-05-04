import ast
import subprocess
import yaml
import os
import socket
import sys

from charmhelpers.core import host, hookenv
from charmhelpers.core.templating import render
from charms.reactive import (
    when, when_not, set_state, remove_state
)
from ipaddress import IPv4Interface
from netifaces import interfaces, ifaddresses, AF_INET
from charms.reactive.helpers import any_file_changed, data_changed
from charms.reactive import hook

from charmhelpers.fetch import apt_install

hooks = hookenv.Hooks()

APT_PKG_NAME = 'prometheus-blackbox-exporter'
SVC_NAME = 'prometheus-blackbox-exporter'
EXECUTABLE = '/usr/bin/prometheus-blackbox-exporter'
PORT_DEF = 9115
BLACKBOX_EXPORTER_YML_TMPL = 'blackbox.yaml.j2'
CONF_FILE_PATH = '/etc/prometheus/blackbox.yml'
AZ_PATH = '/var/lib/juju/az'


def templates_changed(tmpl_list):
    return any_file_changed(['templates/{}'.format(x) for x in tmpl_list])


@when_not('blackbox-exporter.installed')
def install_packages():
    hookenv.status_set('maintenance', 'Installing software')
    config = hookenv.config()
    apt_install(APT_PKG_NAME, fatal=True)
    cmd = ["sudo", "setcap", "cap_net_raw+ep", EXECUTABLE]
    subprocess.check_output(cmd)
    set_state('blackbox-exporter.installed')
    set_state('blackbox-exporter.do-check-reconfig')


def get_modules():
    config = hookenv.config()
    try:
        modules = yaml.safe_load(config.get('modules'))
    except:
        return None

    if 'modules' in modules:
        return yaml.safe_dump(modules['modules'], default_flow_style=False)
    else:
        return yaml.safe_dump(modules, default_flow_style=False)


@when('blackbox-exporter.installed')
@when('blackbox-exporter.do-reconfig-yaml')
def write_blackbox_exporter_config_yaml():
    modules = get_modules()
    render(source=BLACKBOX_EXPORTER_YML_TMPL,
           target=CONF_FILE_PATH,
           context={'modules': modules}
           )
    hookenv.open_port(PORT_DEF)
    set_state('blackbox-exporter.do-restart')
    remove_state('blackbox-exporter.do-reconfig-yaml')


@when('blackbox-exporter.started')
def check_config():
    set_state('blackbox-exporter.do-check-reconfig')


@when('blackbox-exporter.do-check-reconfig')
def check_reconfig_blackbox_exporter():
    config = hookenv.config()

    if data_changed('blackbox-exporter.config', config):
        set_state('blackbox-exporter.do-reconfig-yaml')

    if templates_changed([BLACKBOX_EXPORTER_YML_TMPL]):
        set_state('blackbox-exporter.do-reconfig-yaml')

    remove_state('blackbox-exporter.do-check-reconfig')


@when('blackbox-exporter.do-restart')
def restart_blackbox_exporter():
    if not host.service_running(SVC_NAME):
        hookenv.log('Starting {}...'.format(SVC_NAME))
        host.service_start(SVC_NAME)
    else:
        hookenv.log('Restarting {}, config file changed...'.format(SVC_NAME))
        host.service_restart(SVC_NAME)
    hookenv.status_set('active', 'Ready')
    set_state('blackbox-exporter.started')
    remove_state('blackbox-exporter.do-restart')

def get_az():
    az = None
    if os.path.exists(AZ_PATH):
        az = open(AZ_PATH, 'r').read().strip()
    return az

def get_unit_networks():
    networks = []
    for iface in interfaces():
        if iface == 'lo': continue
        ip_addresses = ifaddresses(iface)
        if AF_INET in ip_addresses:
            for ip_address in ip_addresses[AF_INET]:
                ip_v4 = IPv4Interface("{}/{}".format(ip_address['addr'], ip_address['netmask']))
                networks.append({"iface": iface, "ip": ip_v4.ip.__str__(), "net": ip_v4.network.__str__()})
    return networks

def get_principal_unit_open_ports():
    cmd = "lsof -P -iTCP -sTCP:LISTEN".split()
    result = subprocess.check_output(cmd)
    result = result.decode(sys.stdout.encoding)

    ports = []
    for r in result.split('\n'):
        for p in r.split():
            if '*:' in p:
                ports.append(p.split(':')[1])
    ports = [p for p in set(ports)]

    return ports

@hook('blackbox-peer-relation-{joined,departed}')
def blackbox_peer_departed(peers):
    hookenv.log('Blackbox peer unit joined/departed.')
    set_state('blackbox-exporter.redo-peer-relation')

@when('blackbox-exporter.redo-peer-relation')
def setup_blackbox_peer_relation(peers):
    # Set blackbox-peer relations
    hookenv.log('Running blackbox peer relations.')
    hookenv.status_set('maintenance', 'Configuring blackbox peer relations.')
    for rid in hookenv.relation_ids('blackbox-peer'):
        relation_settings = hookenv.relation_get(rid=rid, unit=hookenv.local_unit())
        relation_settings['principal-unit'] = hookenv.principal_unit()
        relation_settings['principal-hostname'] = socket.gethostname()
        relation_settings['private-address'] = hookenv.unit_get('private-address')
        relation_settings['unit-networks'] = get_unit_networks()
        relation_settings['az'] = get_az()
        relation_settings['unit-ports'] = get_principal_unit_open_ports()
        hookenv.relation_set(relation_id=rid, relation_settings=relation_settings)

    hookenv.status_set('active', 'Ready')
    remove_state('blackbox-exporter.redo-peer-relation')
