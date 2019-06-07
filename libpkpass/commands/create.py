"""This module allows for the creation of passwords"""
import getpass
from builtins import input
from libpkpass.commands.command import Command
from libpkpass.errors import CliArgumentError, PasswordMismatchError, NotThePasswordOwnerError,\
        BlankPasswordError


class Create(Command):
    """This class implements the CLI functionality of creation of passwords"""
    name = 'create'
    description = 'Create a new password entry and encrypt it for yourself'
    selected_args = ['pwname', 'pwstore', 'overwrite', 'stdin', 'identity', 'certpath',
                     'keypath', 'cabundle', 'nopassphrase', 'nosign', 'card_slot',
                     'escrow_users', 'min_escrow', 'noescrow']

    def _run_command_execution(self):
        ####################################################################
        """ Run function for class.                                      """
        ####################################################################
        safe, owner = self.safety_check()
        if safe or self.args['overwrite']:
            password1 = getpass.getpass("Enter password to create: ")
            if password1.strip() == "":
                raise BlankPasswordError
            password2 = getpass.getpass("Enter password to create again: ")
            if password1 != password2:
                raise PasswordMismatchError

            description = input("Description: ")
            authorizer = input("Authorizer: ")
            self.create_pass(password1, description, authorizer)
        else:
            raise NotThePasswordOwnerError(self.args['identity'], owner, self.args['pwname'])

    def _validate_args(self):
        for argument in ['pwname', 'keypath']:
            if argument not in self.args or self.args[argument] is None:
                raise CliArgumentError(
                    "'%s' is a required argument" % argument)
