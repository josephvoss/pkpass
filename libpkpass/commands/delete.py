"""This module allows for the creation of passwords"""
from __future__ import print_function
import sys
from builtins import input
from libpkpass.commands.command import Command
from libpkpass.errors import CliArgumentError, NotThePasswordOwnerError


class Delete(Command):
    """This class implements the CLI functionality of deletion of passwords"""
    name = 'delete'
    description = 'Delete a password in the repository'
    selected_args = Command.selected_args + ['pwname', 'pwstore', 'overwrite', 'stdin', 'keypath', 'card_slot']

    def _run_command_execution(self):
        ####################################################################
        """ Run function for class.                                      """
        ####################################################################
        safe, owner = self.safety_check()
        if safe or self.args['overwrite']:
            self._confirmation()
        else:
            raise NotThePasswordOwnerError(self.args['identity'], owner, self.args['pwname'])

    def _confirmation(self):
        yes = {'yes', 'y', 'ye', ''}
        deny = {'no', 'n'}
        confirmation = input("%s: \nDelete this password?(Defaults yes):"
                             % (self.args['pwname']))
        if confirmation.lower() in yes:
            self.delete_pass()
        elif confirmation.lower() in deny:
            sys.exit()
        else:
            print("please respond with yes or no")
            self._confirmation()

    def _validate_args(self):
        for argument in ['pwname', 'keypath']:
            if argument not in self.args or self.args[argument] is None:
                raise CliArgumentError(
                    "'%s' is a required argument" % argument)
