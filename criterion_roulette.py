#!/usr/bin/env python
import os
import re
import sys
import json
import random
import datetime

from time import sleep
from math import ceil

from pyfiglet import figlet_format


LOGFILE_NAME = 'db.json'
DEBUG_LOGFILE_NAME = 'debug.db.json'

PARTY_SIZE = 4
DEFAULT_ROLE_LIST = ['Tank', 'Healer', 'Melee', 'Ranged']
#DEFAULT_ROLE_LIST = ['T', 'H', 'M', 'R']
SAMPLE_PARTY_LIST = ['Shin', 'Figgy', 'Nari', 'Jing']
SAMPLE_UNDERSIZED_PARTY_LIST = ['Shin', 'Figgy', 'Nari']
DEFAULT_DUNGEON_DICT = {"ASS": "Another Sil'dihn Subterrane",
                        "AMR": "Another Mount Rokkon",
                        "AAI": "Another Aloalo Island"}
SECRET_ROLES = ['Tank', 'Healer', 'Melee']
REQUIRED_ROLES = ['Tank', 'Healer']

PROMPT = '> '
TABLE_MARGINS = 4
INDENT_INTERVAL = 4
MAX_DUNGEON_NAME_LENGTH = max([len(DEFAULT_DUNGEON_DICT[dungeon]) for dungeon in DEFAULT_DUNGEON_DICT])

TBD_STRING = 'Coming soon!'
CONTINUE_STRING = '\nPress Enter to continue...\n'
DIVIDER = '-' * 80
HEADER_MESSAGE = figlet_format('Criterion Roulette', font='slant', width = 60, justify='right') + '\n' + DIVIDER
MAIN_MENU = """Main Menu

    1) Start session
    2) Statistics
    3) Exit
        """


class Session:
    _session_menu = """
    1) Start a new run
    2) View previous run
    3) View session stats
    4) End session
    """


    def __init__(self, session_members=None, dungeon_list=DEFAULT_DUNGEON_DICT, debug=False):
        self.active = True
        self.dungeon_list = dungeon_list
        self.logfile_name = LOGFILE_NAME
        self.member_list = None
        self.run_count = 0
        self.secret_enabled = False
        self.session_id = self.generate_session_id()
        self.session_runs = []
        self.timestamp = str(datetime.datetime.now(tz=datetime.UTC))
        try:
            self.set_member_list(session_members)
        except (TypeError, ValueError) as e:
            print('Error setting member list')
            raise e

        if (debug == True):
            self.logfile_name = DEBUG_LOGFILE_NAME


    def set_member_list(self, member_list=None):
        if member_list is None:
            raise Exception('No members specified!')
        elif type(member_list) is not list:
            raise TypeError('Members must be a list!')
        elif len(member_list) != 4:
            raise ValueError(f'Invalid member count! ({len(member_list)})') 
        self.member_list = member_list


    def generate_session_id(self):
        # For now, just set session_id to the epoch timestamp for the start of the session.
        return int(datetime.datetime.now().timestamp())


    def get_members(self):
        return self.member_list


    def get_session_id(self):
        return self.session_id


    def is_active(self):
        return self.active_status


    def display_session_menu(self):
        clear_screen()
        #print(HEADER_MESSAGE)
        print(f'Session Menu (ID: {self.session_id})\n')
        print('Current Members:')
        print(self.format_current_members())
        print(self._session_menu)


    def display_session_summary(self):
        '''Display the current Session's summary screen (used when ending a Session).'''
        if len(self.session_runs) == 0:
            return None

        clear_screen()

        # Table for # of times each dungeon was selected
        dungeon_counts = self.parse_dungeon_counts()
        print('\nSession Totals:\n')
        for dungeon in self.dungeon_list.keys():
            print(f'{"":{INDENT_INTERVAL*4}}{self.dungeon_list[dungeon]+":":32s}{dungeon_counts[dungeon]!s}')
        print(f'\n{"":{INDENT_INTERVAL*4}}{"Overall:":32s}{sum(dungeon_counts.values())!s}')
        print('\n')

        # Table for # of times each member was assigned each role
        print('Role Assigments:\n')
        print(self.render_role_assignment_table())
        for member in self.member_list:
            print(f'{"":{INDENT_INTERVAL}}{self.render_member_summary(member)}')

        # Scoreboard Line
        scoreboard_line = self.render_scoreboard_line(self.session_runs, dungeon_counts)
        print('\n\n')
        print('Scoreboard Entry:\n')
        print(f'{"":{INDENT_INTERVAL}}{scoreboard_line}')

        input(CONTINUE_STRING)
        
        return None


    def display_run_info(self, run_list=None):
        '''Display (currently) the "raw" data from the DungeonRuns created in the current Session.'''
        # TODO: to be re-written, currently displaying pseudo-json string format
        if run_list is None:
            run_list = self.session_runs
       
        clear_screen()

        if len(run_list) == 0:
            print('No runs recorded this session!')
            input(CONTINUE_STRING)
            return None

        for run in run_list:
            s = '{'
            
            dungeon = run.get_dungeon()
            party = run.get_party()
            
            s += f'"dungeon": "{dungeon}"'

            for member, role in party.items():
                s += f', "{member}": "{role}"'

            s += '}'
            
            print(s)
       
        input(CONTINUE_STRING)
        return True


    def render_run_info(self, run=None):
        '''Return a table-form output string for an input DungeonRun object''' 
        if run is None:
            return None        

        rendered_info = ''
        current_dungeon = run.get_dungeon()
        current_party = run.get_party()
        current_id = run.get_id()

        rendered_info += f'Run # {current_id}\n\n'
        rendered_info += f'Dungeon Selection:\n\n{"": <{INDENT_INTERVAL}}{self.dungeon_list[current_dungeon]:^{MAX_DUNGEON_NAME_LENGTH}}\n\n'
        rendered_info += f'Role Selection:\n\n'
        for member in current_party:
            offset = (ceil(MAX_DUNGEON_NAME_LENGTH / 2)) + 2
            rendered_info += f'{member:>{offset}}{"":3}{current_party[member]}\n'
        
        return rendered_info

    
    def render_scoreboard_line(self, run_list=None, dungeon_counts=None):
        '''Returns a formatted one-line string to enter into the external scoreboard record.'''
        if run_list is None or dungeon_counts is None:
            return None

        # renders a string in the following format:
        # Day ##() - 6, ASS, ASS, ASS, ASS, AAI, ASS ---- 5/0/1
        # ^     #1    ^ ^           #2               ^^   #3   ^
        rendered_string = f'Day ##   - {sum(dungeon_counts.values())}, '
        s = ', '.join([run.get_dungeon() if run.get_num_secrets() == 0 else run.get_dungeon()+'*' for run in run_list])
        rendered_string += s + ' '
        rendered_string = f'{rendered_string:-<47} {"/".join([str(dungeon_counts[entry]) for entry in self.dungeon_list])}'

        return rendered_string


    def render_log_from_run(self, run=None):
        '''Return a JSON format log-string for an input DungeonRun'''
        if run is None:
            return None

        run_attr = {} 
        run_attr['timestamp'] = str(datetime.datetime.now(tz=datetime.UTC))
        run_attr['session_id'] = self.session_id
        run_attr['members'] = self.member_list
        for key, value in run.__dict__.items():
            if key == 'id':
                key = 'run_id'
            run_attr[key] = value
        #run_attr = run.__dict__

        return json.dumps(run_attr)


    def render_role_assignment_table(self):
        '''Return a formatted one-line string containing the headers for the Role Assignment table.'''
        rendered_string = f'{"":{INDENT_INTERVAL*4}}'
        for role in DEFAULT_ROLE_LIST:
            rendered_string += f'{role}{"":{TABLE_MARGINS}}'

        return rendered_string


    def render_member_summary(self, member=None):
        '''Return a formatted one-line string containing the role counts from the current Session for an input member.'''
        if member is None:
            return None
        
        rendered_string = f'{member:>10}{"":2}'
        for role in DEFAULT_ROLE_LIST:
            role_count = len([entry for entry in self.session_runs if entry.get_party()[member] == role])
            rendered_string += f'{role_count!s:>{len(role)}}{"":{TABLE_MARGINS}}'

        return rendered_string
        

    def get_current_run(self):
        '''Return a formatted multi-line string from the most recently generated DungeonRun'''
        if len(self.session_runs) == 0:
            return 'No runs recorded this session!'

        return 'Current Run\n------------\n' + self.render_run_info(self.session_runs[-1])


    def get_previous_run(self):
        '''Return a formatted multi-line string from the previously generated DungeonRun'''
        if len(self.session_runs) < 2:
            return 'Only one run recorded this session!'

        return 'Previous Run\n------------\n' + self.render_run_info(self.session_runs[-2])
 

    def format_current_members(self):
        return ', '.join(self.member_list)


    def parse_dungeon_counts(self):
        '''Return a dict of dungeon, dungeon_count pairings from the current Session'''
        counts = {}
        for dungeon in self.dungeon_list:
            filtered_dungeon_list = [entry for entry in self.session_runs if entry.get_dungeon() == dungeon]
            counts[dungeon] = len(filtered_dungeon_list)
        
        return counts


    def start_new_run(self):
        '''Returns a new DungeonRun object using the current Session configuration.'''
        #if dungeon_list is None or party_list is None:
        #    raise Exception('Incorrect starting parameters for a new run')
        
        try:
            run = DungeonRun(run_id=len(self.session_runs)+1, dungeon_list=self.dungeon_list, member_list=self.member_list)
        except Exception as e:
            print(e)
            return None        
        #print(self.render_run_info(run))
        
        if self.secret_enabled:
            secret = self.roll_for_secret()
            if secret is not None:
                run.activate_secret(secret)

        self.session_runs.append(run)

        return run


    def roll_for_secret(self):
        if random.random() < .05:
            return random.choice(SECRET_ROLES)
        
        return None


    def log_run(self, logfile=None, run=None):
        if logfile is None or run is None:
            return None        
        log_entry = self.render_log_from_run(run)

        with open(logfile, 'a') as f:
            f.write(log_entry + '\n')

        return log_entry


    def start(self):
        response = None

        print('Session starting...')
        clear_screen()
        
        while self.active:
            self.display_session_menu()
            if response is not None:
                print(response)
            user_selection = wait_for_user_input() 

            if user_selection == '4': # Exit
                self.active = False
                self.display_session_summary()
                break
            elif user_selection == '1': # Start a new run
                r = self.start_new_run()
                self.log_run(logfile = self.logfile_name, run=r)
                response = self.get_current_run()
            elif user_selection == '2': # View previous run
                response = self.get_previous_run()
            elif user_selection == '3': # View session stats
                self.display_run_info(self.session_runs)
            elif user_selection == '2357':
                self.secret_enabled = not self.secret_enabled
                response = f'Secret {"enabled" if self.secret_enabled else "disabled"}!  {self.secret_enabled}'
            else:
                if response is not None and len(self.session_runs) > 0:
                    response = self.get_current_run()
            #input(CONTINUE_STRING)


class DungeonRun: 

    def __init__(self, run_id=None, dungeon_list=None, member_list=None):
        self.dungeon = None
        self.party = None
        self.id = run_id
        self.secrets_triggered = 0
        try:
            self.dungeon = self.select_dungeon(dungeon_list)
            self.party = self.select_party(member_list)
        except Exception as e:
            print(e)


    def select_party(self, member_list=None):
        party_with_roles = {}
        remaining_role_list = DEFAULT_ROLE_LIST.copy()
        
        for member in member_list:
            party_with_roles[member], remaining_role_list = self.assign_role(remaining_role_list)
        
        return party_with_roles


    def assign_role(self, role_list=[]):
        role = random.choice(role_list)
        role_list.remove(role)
        return role, role_list


    def select_dungeon(self, dungeon_list=None):
        if dungeon_list is None:
            raise Exception('No dungeons provided!')
        return random.choice(list(dungeon_list.keys()))

    def activate_secret(self, replacement_role=None):
        if replacement_role is None:
            return None
        self.secrets_triggered += 1
        for member, role in self.party.items():
            if role not in REQUIRED_ROLES and role != replacement_role:
                self.party[member] = replacement_role
                break
        return None


    def get_dungeon(self):
        return self.dungeon


    def get_party(self):
        return self.party


    def get_id(self):
        return self.id

    def get_num_secrets(self):
        return self.secrets_triggered

def register_members(debug=False):
    '''Return a validated list of members from user input.'''
    if debug:
        return SAMPLE_PARTY_LIST

    print('Please enter members for this session')
    raw_input = input(PROMPT)

    if raw_input == '':
        member_list = SAMPLE_PARTY_LIST
        print('No input detected. Using Sample Party List')
        input(CONTINUE_STRING)
    else:
        #member_list = [member.strip().capitalize() for member in raw_input.split(' ') ]
        member_list = [member.strip().capitalize() for member in re.sub(r'\s{2,}', ' ', raw_input).split(' ')]
        try:
            validate_member_list(member_list)
        except ValueError as e:
            raise e

    return member_list


def validate_member_list(member_list=None):
    '''Raise a ValueError if input member_list does not meet PARTY_SIZE with no duplicates.'''
    if member_list is None:
        return False
    elif len(member_list) != PARTY_SIZE:
        raise ValueError('Incorrect number of party members!\n')
    elif len(member_list) != len(set(member_list)):
        raise ValueError('No duplicate names allowed!')
    
    return True


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(HEADER_MESSAGE)


def display_main_menu():
    clear_screen()
    print(MAIN_MENU)


def wait_for_user_input(options={}):
#    user_selection = None
#    while user_selection is None:
#        # print('Getting input')
#        user_selection = input(PROMPT)
#     return user_selection
    return input(PROMPT)


def create_session(member_list=None, debug=False):
    while member_list is None:
        try:
            if (debug == True):
                member_list = SAMPLE_PARTY_LIST
                session = Session(member_list, debug=True)
                return session
            member_list = register_members(debug=False)
        except ValueError as e:
            print(e)
            member_list = None
    
    session = Session(member_list)
    return session


def run():
    response = None
    while True:
        display_main_menu()
        if response is not None:
            print(response)
        user_selection = wait_for_user_input()
        if user_selection == '1':
            try:
                session = create_session()
                session.start()
            except Exception as e:
                response = e
                continue
        elif user_selection == '2':
            response = TBD_STRING
        elif user_selection == '3':
            print('Thanks for playing!')
            return 0
        elif user_selection == '0':
                session = create_session(debug=True)
                session.start()
    return 1

if __name__ == "__main__":
    sys.exit(run())
