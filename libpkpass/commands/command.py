"""This module is a generic for all pkpass commands"""

from __future__ import print_function
import sys
import getpass
import json
import os
import yaml
from six import iteritems as iteritems
from libpkpass.commands.arguments import ARGUMENTS as arguments
from libpkpass.password import PasswordEntry
from libpkpass.identities import IdentityDB
from libpkpass.errors import NullRecipientError, CliArgumentError, FileOpenError, GroupDefinitionError


class Command(object):
    ##########################################################################
    """ Base class for all commands.  Auotmatically registers with cli subparser
    and provides run execution for itself.                                     """
    ##########################################################################

    name = None
    description = None
    selected_args = None
    passphrase = None

    def __init__(self, cli):
        ##################################################################
        """ Intialization function for class. Register with argparse   """
        ##################################################################
        self.cli = cli
        #default certpath to none because connect string is allowed
        self.args = {'identity': getpass.getuser(),
                     'pwstore': './passwords',
                     'certpath': None,
                     'keypath': './private',
                     'cabundle': './certs/ca-bundle',
                     'time': 10,
                     'noverify': None,
                     'card_slot': None,
                     'min_escrow': None,
                     'escrow_users': None}
        self.recipient_list = []
        self.identities = IdentityDB()
        cli.register(self, self.name, self.description)

    def register(self, parser):
        ####################################################################
        """ Registration function for class. Register with argparse      """
        ####################################################################
        for arg in sorted(self.selected_args):
            parser.add_argument(
                *arguments[arg]['args'],
                **arguments[arg]['kwargs'])

    def run(self, parsedargs):
        ##################################################################
        """ Passes the argparse Namespace object of parsed arguments   """
        ##################################################################
        self._run_command_setup(parsedargs)
        self._run_command_execution()

    def _run_command_setup(self, parsedargs):
        ##################################################################
        """ Passes the argparse Namespace object of parsed arguments   """
        ##################################################################

        # Build a dict out of the argparse args Namespace object and a dict from any
        # configuration files and merge the two with cli taking priority
        cli_args = vars(parsedargs)

        config_args = self._get_config_args(cli_args['config'])
        self.args.update(config_args)

        fles = ['keypath', 'cabundle', 'pwstore']
        for key, value in iteritems(cli_args):
            if value is not None or key not in self.args:
                self.args[key] = value
            if key in fles and not os.path.exists(self.args[key]):
                raise FileOpenError(self.args[key], "No such file or directory")

        #print(self.args)
        if self.args['escrow_users']:
            self.args['escrow_users'] = self.args['escrow_users'].split(",")
        self._validate_combinatorial_args()
        self._validate_args()

        if self.args['subparser_name'] != 'show' and self.args['noverify'] is True:
            self.args['noverify'] = False

        if 'nopassphrase' in self.selected_args and not self.args['nopassphrase']:
            self.passphrase = getpass.getpass("Enter Pin/Passphrase: ")

        # Build the list of recipients that this command will act on
        self._build_recipient_list()

        connectmap = None
        if 'connect' in self.args and self.args['connect']:
            connectmap = json.loads(self.args['connect'])

        # If there are defined repositories of keys and certificates, load them
        self.identities.load_certs_from_directory(
            self.args['certpath'],
            self.args['cabundle'],
            connectmap,
            self.args['noverify'],
            self.args['nocache'] if 'nocache' in self.args else False)
        self.identities.load_keys_from_directory(self.args['keypath'])
        self._validate_identities()

    def create_pass(self, password1, description, authorizer, recipient_list=None):
        ####################################################################
        """ Run function for class.                                      """
        ####################################################################
        password_metadata = {}
        password_metadata['description'] = description
        password_metadata['authorizer'] = authorizer
        password_metadata['creator'] = self.args['identity']
        password_metadata['name'] = self.args['pwname']
        if self.args['min_escrow']:
            password_metadata['min_escrow'] = self.args['min_escrow']
        if recipient_list is None:
            recipient_list = [self.args['identity']]

        password = PasswordEntry(**password_metadata)

        password.add_recipients(secret=password1,
                                distributor=self.args['identity'],
                                recipients=recipient_list,
                                identitydb=self.identities,
                                passphrase=self.passphrase,
                                card_slot=self.args['card_slot'],
                                escrow_users=self.args['escrow_users'],
                                minimum=self.args['min_escrow']
                               )

        password.write_password_data(os.path.join(
            self.args['pwstore'], self.args['pwname']), overwrite=self.args['overwrite'])

    def _run_command_execution(self):
        ##################################################################
        """ Passes the argparse Namespace object of parsed arguments   """
        ##################################################################
        raise NotImplementedError

    def _build_recipient_list(self):
        try:
            if 'groups' in self.args and self.args['groups'] is not None:
                self.recipient_list += self._parse_group_membership()
            if 'users' in self.args and self.args['users'] is not None:
                self.recipient_list += self.args['users'].split(',')
            self.recipient_list = [x.strip() for x in self.recipient_list]
            for user in self.recipient_list:
                if str(user) == '':
                    raise NullRecipientError
        except KeyError:  # If this is a command with no users, don't worry about it
            pass

    def _parse_group_membership(self):
        member_list = []
        try:
            for group in self.args['groups'].split(','):
                member_list += self.args[group.strip()].split(',')
            return member_list
        except KeyError as err:
            raise GroupDefinitionError(str(err))

    def _get_config_args(self, config):
        try:
            with open(config, 'r') as fname:
                config_args = yaml.safe_load(fname)
            if config_args is None:
                config_args = {}
            return config_args
        except IOError:
            print("No .pkpassrc file found, consider running ./setup.sh")
            return {}

    def _validate_args(self):
        raise NotImplementedError

    def _validate_combinatorial_args(self):
        ##################################################################
        """ This is a weird function name so: combinatorial in this case
            means that one of the 'combinatorial' arguments are required
            however, not all of them are necessarily required.
            Ex: We need certs, we can get this from certpath or connect
            we do not need both of these arguments but at least one is
            required"""
        ##################################################################
        # we want a multi-dim of lists, this way if more combinations come up
        # that would be required in a 1 or more capacity, we just add
        # a list to this list
        args_list = [['certpath', 'connect']]
        for arg_set in args_list:
            valid = False
            for arg in arg_set:
                if arg in self.args and self.args[arg] != None:
                    valid = True
                    break
            if not valid:
                raise CliArgumentError(
                    "'%s' or '%s' is required" % tuple(arg_set))

    def _validate_identities(self):
        for recipient in self.recipient_list:
            if recipient not in self.identities.iddb.keys():
                raise CliArgumentError(
                    "Error: Recipient '%s' is not in the recipient database" %
                    recipient)

        if self.args['identity'] not in self.identities.iddb.keys():
            raise CliArgumentError(
                "Error: Your user '%s' is not in the recipient database" %
                self.args['identity'])

    def _print_debug(self):
        print(self.recipient_list)
        print(self.identities.iddb.keys())

    def progress_bar(self, value, endvalue, bar_length=20):
        percent = float(value) / endvalue
        arrow = '-' * int(round(percent * bar_length)-1) + '>'
        spaces = ' ' * (bar_length - len(arrow))
        sys.stdout.write("\rPercent: [{0}] {1}%".format(arrow + spaces, int(round(percent * 100))))
        sys.stdout.flush()
