from __future__ import print_function

from contextlib import contextmanager
import errno
import logging
import os
from shutil import (
    copytree,
    rmtree,
)
import subprocess
from time import time
from tempfile import mkdtemp
import uuid
import yaml


@contextmanager
def temp_dir(parent=None):
    directory = mkdtemp(dir=parent, prefix='cwr_tst_')
    try:
        yield directory
    finally:
        try:
            rmtree(directory)
        except OSError:
            run_command('sudo rm -rf {}'.format(directory))


def configure_logging(log_level):
    logging.basicConfig(
        level=log_level, format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


def ensure_dir(path, parent=None):
    path = os.path.join(parent, path) if parent else path
    try:
        os.mkdir(path)
        return path
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def run_command(command, verbose=True):
    """Execute a command and maybe print the output."""
    if isinstance(command, str):
        command = command.split()
    if verbose:
        logging.info('Executing: {}'.format(command))
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = ''
    while proc.poll() is None:
        status = proc.stdout.readline()
        if status:
            logging.info(status.rstrip())
            output += status
    if proc.returncode != 0 and proc.returncode is not None:
        output, error = proc.communicate()
        logging.info("ERROR: run_command failed: {}".format(error))
        e = subprocess.CalledProcessError(proc.returncode, command, error)
        e.stderr = error
        raise e
    return output


def get_juju_home():
    home = os.environ.get('JUJU_HOME')
    if home is None:
        home = os.path.join(os.environ.get('HOME'), 'cloud-city')
    return home


def copytree_force(src, dst, ignore=None):
    if os.path.exists(dst):
        rmtree(dst)
    copytree(src, dst, ignore=ignore)


def rename_env(from_env, to_env, env_path):
    with open(env_path, 'r') as f:
        env = yaml.load(f)
    new_env = to_env + from_env
    env['environments'][new_env] = env['environments'].pop(from_env)
    with open(env_path, 'w') as f:
        yaml.dump(env, f, indent=4, default_flow_style=False)
    return new_env


def juju_run(command, args='', e=''):
    e = '-e {}'.format(e) if e else e
    return run_command('juju {} {} {}'.format(command, e, args))


def juju_status(e=''):
    return juju_run('status', e=e)


def generate_test_id():
    return uuid.uuid4().hex


def cloud_from_env(env):
    if 'aws' in env.lower():
        if 'china' in env.lower():
            return 'aws-china'
        return 'aws/us-west-1'
    if 'azure' in env.lower():
        return 'azure/westus'
    if 'gce' in env.lower() or 'google' in env.lower():
        return 'google/europe-west1'
    if 'joyent' in env.lower():
        return 'joyent/us-sw-1'
    if 'power8' in env.lower():
        return 'borbein-maas'
    if 'ob-maas' in env.lower():
        return 'ob-maas'
    return None


def get_temp_controller_name(controller_name):
    suffix = os.environ.get('BUILD_NUMBER') or str(time()).split('.')[0]
    return "{}-{}".format(controller_name, suffix)
