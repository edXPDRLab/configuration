"""VPC Tools.

Usage:
    vpc-tools.py ssh-config (vpc <vpc_id> | stack-name <stack_name>) identity-file <identity_file> user <user> [(config-file <config_file>)] [(strict-host-check <strict_host_check>)]
    vpc-tools.py (-h --help)
    vpc-tools.py (-v --version)

Options:
    -h --help       Show this screen.
    -v --version    Show version.

"""
import boto
from docopt import docopt
from vpcutil import vpc_for_stack_name
from vpcutil import stack_name_for_vpc
from collections import defaultdict


VERSION="vpc tools 0.1"
DEFAULT_USER="ubuntu"
DEFAULT_HOST_CHECK="ask"

JUMPBOX_CONFIG = """
    Host {jump_box}
      HostName {ip}
      IdentityFile {identity_file}
      ForwardAgent yes
      User {user}
      StrictHostKeyChecking {strict_host_check}
    """

HOST_CONFIG = """
    # Instance ID: {instance_id}
    Host {name}
      ProxyCommand ssh {config_file} -W %h:%p {jump_box}
      HostName {ip}
      IdentityFile {identity_file}
      ForwardAgent yes
      User {user}
      StrictHostKeyChecking {strict_host_check}
    """


def dispatch(args):

    if args.get("ssh-config"):
        _ssh_config(args)

def _ssh_config(args):
    if args.get("vpc"):
      vpc_id = args.get("<vpc_id>")
      stack_name = stack_name_for_vpc(vpc_id)
    elif args.get("stack-name"):
      stack_name = args.get("<stack_name>")
      vpc_id = vpc_for_stack_name(stack_name)
    else:
      raise Exception("No vpc_id or stack_name provided.")

    vpc = boto.connect_vpc()

    identity_file = args.get("<identity_file>")
    user = args.get("<user>")
    config_file = args.get("<config_file>")
    strict_host_check = args.get("<strict_host_check>")

    if not user:
      user = DEFAULT_USER

    if not strict_host_check:
      strict_host_check = DEFAULT_HOST_CHECK

    if config_file:
      config_file = "-F {}".format(config_file)
    else:
      config_file = ""

    jump_box = "{stack_name}-jumpbox".format(stack_name=stack_name)
    friendly = "{stack_name}-{logical_id}-{instance_number}"
    id_type_counter = defaultdict(int)

    reservations = vpc.get_all_instances(filters={'vpc-id' : vpc_id})

    for reservation in reservations:
        for instance in reservation.instances:

            if 'role' in instance.tags:
                logical_id = instance.tags['role']
            elif 'group' in instance.tags:
                logical_id = instance.tags['group']
            else:
                logical_id = instance.tags['aws:cloudformation:logical-id']
            instance_number = id_type_counter[logical_id]
            id_type_counter[logical_id] += 1

            if logical_id == "BastionHost" or logical_id == 'bastion':

                print JUMPBOX_CONFIG.format(
                    jump_box=jump_box,
                    ip=instance.ip_address,
                    user=user,
                    identity_file=identity_file,
                    strict_host_check=strict_host_check)

            # Print host config even for the bastion box because that is how
            # ansible accesses it.
            print HOST_CONFIG.format(
                name=instance.private_ip_address,
                jump_box=jump_box,
                ip=instance.private_ip_address,
                user=user,
                identity_file=identity_file,
                config_file=config_file,
                strict_host_check=strict_host_check,
                instance_id=instance.id)

            #duplicating for convenience with ansible
            name = friendly.format(stack_name=stack_name,
                                   logical_id=logical_id,
                                   instance_number=instance_number)

            print HOST_CONFIG.format(
                name=name,
                jump_box=jump_box,
                ip=instance.private_ip_address,
                user=user,
                identity_file=identity_file,
                config_file=config_file,
                strict_host_check=strict_host_check,
                instance_id=instance.id)

if __name__ == '__main__':
    args = docopt(__doc__, version=VERSION)
    dispatch(args)
