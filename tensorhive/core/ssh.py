from tensorhive.core.utils.decorators import memoize, timeit
from tensorhive.config import SSH
from pssh.clients.native import ParallelSSHClient
from pssh.exceptions import AuthenticationException
from typing import Optional, Dict, Tuple, Generator, List
from paramiko.rsakey import RSAKey
from paramiko.ed25519key import Ed25519Key
from pathlib import PosixPath
import pssh
import logging
log = logging.getLogger(__name__)

__author__ = '@micmarty, @roscisz'
"""
This module provides a universal and stateless API for SSH-related tasks.

Author's note:
It has similar functionality to `SSHConnectionManager` on purpose -
the goal is to gradually replace chunks of code where it's currently used
without breaking compatibility everywhere.
(SSHConnectionManager has unnecessary boilerplate and stateful behaviour).
"""

# Typing aliases
HostConfig = Dict[str, str]
HostsConfig = Dict[str, HostConfig]
ProxyConfig = Dict[str, str]
Hostname = str
Username = str
CommandResult = Dict[Hostname, pssh.output.HostOutput]

KEYS = {
    "rsa": RSAKey,
    "ed25519key": Ed25519Key,
}


def build_dedicated_config_for(host: Hostname, user: Username) -> Tuple[HostsConfig, Optional[ProxyConfig]]:
    """Takes off the responsibility for building correct HostsConfig manually.

    This function is supposed to provide high-level interface for providing
    valid `config` and `pconfig` parameter to `get_client()` function.
    """
    assert host and user, 'Arguments must not be None!'
    assert host in SSH.AVAILABLE_NODES
    hosts_config = {
        host: {
            'user': user,
            'pkey': SSH.KEY_FILE,
            'port': SSH.AVAILABLE_NODES[host]['port']
        }
    }
    # Read config extracted from hosts_config.ini (proxy is common for all hosts)
    pconfig = SSH.PROXY
    return hosts_config, pconfig


@memoize
def get_client(config: HostsConfig, pconfig: Optional[ProxyConfig] = None, **kwargs) -> ParallelSSHClient:
    """Builds and returns an ssh client object for given configuration.

    Client is fetched directly from cache if identical arguments were used recently.
    """
    if pconfig is None:
        pconfig = {}

    return ParallelSSHClient(
        hosts=config.keys(),
        host_config=config,
        pkey=SSH.KEY_FILE,
        proxy_host=pconfig.get('proxy_host'),
        proxy_user=pconfig.get('proxy_user'),
        proxy_port=pconfig.get('proxy_port'),
        num_retries=0,
        **kwargs)


def run_command(client: ParallelSSHClient, command: str) -> CommandResult:
    """Executes identical command on all hosts attached to client.

    Will wait until all hosts complete the command execution or timeout is reached.
    Re-raises pssh exceptions.
    # TODO Handle more specific exceptions
    """
    # stop_on_errors -> allows others hosts to execute when one crashes, combine exceptions
    # output is like: (hostname, host_output)
    try:
        result = client.run_command(command, stop_on_errors=False)
        client.join(result)
    except pssh.exceptions.Timeout:
        log.warning('Command `{}` reached time limit'.format(command))
        raise
    except pssh.exceptions.ProxyError as e:
        log.error('Could not connect to proxy server, reason: {}'.format(e))
        raise
    except Exception as e:
        log.critical(e)
        raise  # FIXME Find out what throws this exception
    else:
        log.debug('Command `{}` finished'.format(command))
        return result


def get_stdout(host: Hostname, output: pssh.output.HostOutput) -> Optional[str]:
    """Unwraps stdout generator for given hostname.

    Re-raises exceptions that occured during command execution.
    Returns a single, usually multi-line string or None
    # TODO Handle more exceptions
    """
    try:
        host_result = output[host]
        if host_result.exception:
            raise host_result.exception
        return '\n'.join(list(host_result.stdout))
    except KeyError:
        log.error('Could not unwrap HostOutput object for {}'.format(host))
        raise
    except (TypeError, ):
        log.warning('Could not extract stdout for {}: {}'.format(host, output))
        return None
    except AuthenticationException:
        log.warning('Could not authenticate SSH connection for {}: {}'.format(host, output))
        return None
    except Exception as e:
        log.critical(e)
        # Base for all pssh exceptions: https://github.com/ParallelSSH/parallel-ssh/blob/master/pssh/exceptions.py
        # client.reset_output_generators(output)
        raise


def succeeded(host: Hostname, output: pssh.output.HostOutput) -> bool:
    """Checks whether command's output was executed without any exception and exit code was 0."""
    return (output.exception is None) and (output.exit_code == 0)


def generate_cert(path, replace=False, key_cls="rsa"):
    path.touch(mode=0o600, exist_ok=replace)
    key = KEYS[key_cls].generate(2048)
    key.write_private_key_file(str(path))
    return key


def init_ssh_key(path: PosixPath, key_cls="rsa"):
    if path.exists():
        key = KEYS[key_cls].from_private_key_file(str(path))
        log.info('[⚙] Using existing SSH key in {}'.format(path))
    else:
        key = generate_cert(path, key_cls)
        log.info('[⚙] Generated SSH key in {}'.format(path))
    return key


def node_tty_sessions(connection) -> List[Dict]:
    '''Executes shell command in order to fetch all active terminal sessions'''
    command = 'who'
    output = connection.run_command(command)

    # FIXME Assumes that only one node is in connection
    for _, host_out in output.items():
        result = _parse_who_output(host_out.stdout)
    return result


def _parse_who_output(stdout: Generator) -> List[Dict]:
    '''
    Transforms command output into a dictionary
    Assumes command was: 'who | grep <username>'
    '''
    stdout_lines = list(stdout)  # type: List[str]

    # Empty stdout
    if stdout_lines is None:
        return None

    def as_dict(line):
        columns = line.split()
        return {
            # I wanted it to be more explicit and flexible (even if it could be done better)
            'USER': columns[0],
            'TTY': columns[1]
        }

    return [as_dict(line) for line in stdout_lines]
