"""This Modules allows for distributing created passwords to other users"""
from __future__ import print_function
import fnmatch
import os
from builtins import input
import libpkpass.util as util
from libpkpass.commands.command import Command
from libpkpass.passworddb import PasswordDB
from libpkpass.password import PasswordEntry
from libpkpass.errors import CliArgumentError


class Distribute(Command):
    """This Class implements the CLI functionality for ditribution"""
    name = 'distribute'
    description = 'Distribute existing password entry/ies to another entity [matching uses python fnmatch]'
    selected_args = Command.selected_args + ['pwname', 'pwstore', 'users', 'groups', 'stdin',
                                             'min_escrow', 'escrow_users', 'keypath', 'nopassphrase',
                                             'nosign', 'card_slot', 'noescrow']

    def _run_command_execution(self):
        ####################################################################
        """ Run function for class.                                      """
        ####################################################################
        passworddb = PasswordDB()
        passworddb.load_from_directory(self.args['pwstore'])
        filtered_pdb = util.dictionary_filter(
            os.path.join(self.args['pwstore'], self.args['pwname']),
            passworddb.pwdb,
            [self.args['identity'], 'recipients']
        )
        print("The following password files have matched:")
        print(*filtered_pdb.keys(), sep="\n")
        correct_distribution = input("Is this list correct? (y/N) ")
        if correct_distribution and correct_distribution.lower()[0] == 'y':
            passworddb.pwdb = filtered_pdb
            db_len = len(passworddb.pwdb.keys())
            i = 0
            self.progress_bar(i, db_len)
            for dist_pass, _ in passworddb.pwdb.items():
                password = PasswordEntry()
                password.read_password_data(dist_pass)
                if self.args['identity'] in password.recipients.keys():
                    # we shouldn't modify escrow on distribute
                    self.args['min_escrow'] = None
                    self.args['escrow_users'] = None
                    plaintext_pw = password.decrypt_entry(
                        self.identities.iddb[self.args['identity']],
                        passphrase=self.passphrase,
                        card_slot=self.args['card_slot'])

                    password.add_recipients(secret=plaintext_pw,
                                            distributor=self.args['identity'],
                                            recipients=self.recipient_list,
                                            identitydb=self.identities,
                                            passphrase=self.passphrase,
                                            card_slot=self.args['card_slot'],
                                            pwstore=self.args['pwstore']
                                           )

                    password.write_password_data(dist_pass)
                    i += 1
                    self.progress_bar(i, db_len)
            # format the progress bar appropriately after the loop
            print("")
        else:
            print("Exiting due to wrong password list")

    def _validate_args(self):
        for argument in ['pwname', 'keypath']:
            if argument not in self.args or self.args[argument] is None:
                raise CliArgumentError(
                    "'%s' is a required argument" % argument)
