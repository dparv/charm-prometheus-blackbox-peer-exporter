import yaml

from charmhelpers.core import host, hookenv
from charmhelpers.core.templating import render
from charms.reactive import (
    when, when_not, set_state, remove_state
)
from charms.reactive.helpers import any_file_changed, data_changed
from charms.layer import snap


SNAP_NAME = 'prometheus-blackbox-exporter'
SVC_NAME = 'snap.prometheus-blackbox-exporter.daemon'
PORT_DEF = 9115
BLACKBOX_EXPORTER_YML_TMPL = 'blackbox.yaml.j2'
CONF_FILE_PATH = '/var/snap/prometheus-blackbox-exporter/current/blackbox.yml'


def templates_changed(tmpl_list):
    return any_file_changed(['templates/{}'.format(x) for x in tmpl_list])


@when_not('blackbox-exporter.installed')
def install_packages():
    hookenv.status_set('maintenance', 'Installing software')
    config = hookenv.config()
    channel = config.get('snap_channel', 'stable')
    snap.install(SNAP_NAME, channel=channel, force_dangerous=False)
    set_state('blackbox-exporter.installed')
    set_state('blackbox-exporter.do-check-reconfig')


def get_modules():
    config = hookenv.config()
    try:
        modules = yaml.safe_load(config.get('modules'))
    except:
        return None

    if 'modules' in modules:
        return modules['modules']
    else:
        return modules


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
@when('blackbox-exporter.started')
@when('blackbox-exporter.available') # Relation name is "blackbox-exporter"
def configure_blackbox_exporter_relation(target):
    target.configure(PORT_DEF)
