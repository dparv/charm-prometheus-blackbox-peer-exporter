import subprocess
import yaml

from charmhelpers.core import host, hookenv
from charmhelpers.core.templating import render
from charms.reactive import (
    when, when_not, set_state, remove_state
)
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


# Relations
#@when('blackbox-exporter.started')
#@when('blackbox-peer.connected','blackbox-peer.joined','blackbox-peer.departed')
@hook('blackbox-peer-relation-{joined,changed}','blackbox-exporter-relation-{joined,changed}')
def configure_blackbox_exporter_relation(peers):
    targets = []
    for rid in hookenv.relation_ids('blackbox-peer'):
        for unit in hookenv.related_units(rid):
            addr = hookenv.relation_get('private-address', rid=rid, unit=unit)
            targets.append(addr)

    relation_settings = {}
    relation_settings['targets'] = targets
    relation_settings['ip_address'] = hookenv.unit_get('private-address')
    relation_settings['port'] = PORT_DEF
    relation_settings['job_name'] = hookenv.principal_unit()
    relation_settings['module'] = get_module()

    for rel_id in hookenv.relation_ids('blackbox-exporter'):
        hookenv.relation_set(relation_id=rel_id, relation_settings=relation_settings)

def get_module():
    # TODO(dparv): rewrite to query the principal service and provide
    # reasonable modules to probe - http/https/ssl certs/ssh/icmp/etc.
    return 'icmp'
