### PL Fixtures
### DB Insert
### Send Prediction Template

import configparser
from event import Event
from premier_league import PL

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')

send_hrs_prior_deadline=int(parser.get('rules','send_hrs_prior_deadline'))

welcome_back_template_file = parser.get('message_templates','welcome_back')
upcoming_fixtures_template_file = parser.get('message_templates','upcoming_fixtures')

class InitialMessage(Event):

    def __init__(self) -> None:

        super().__init__()

        self.pl = PL()
        
        self.gw_soon = False
        self.gw = None
        self.deadline = None
        self.fixtures = None
        self.message_sent_prior = False

        # get fixtures         
        upcoming = self.pl.get_upcoming_fixtures(send_hrs_prior_deadline)

        if upcoming:

            # there is an upcoming gameweek
            self.gw_soon = True
            self.gw = upcoming[0]
            self.deadline = upcoming[1]
            self.fixtures = upcoming[2]

            # check if already sent
            query = (f"SELECT * FROM fixtures WHERE gw={self.gw};")
            curr_gw_fixtures = self.read_query(query)
            if len(curr_gw_fixtures)>0:
                # prediction reminder for this week already sent
                self.message_sent_prior = True


    def insert_fixtures(self):

        self.write_insert('fixtures', self.fixtures)
    

    def send_fixtures_message(self):

        # query teams
        query = ("SELECT * FROM teams;")
        teams_result = Action.read_query(query)
        teams = {team['team_id']: team['team_name'] for team in teams_result}

        # Welcome Message
        with open(welcome_back_template_file, 'r') as file:
            welcome_back_message_body = file.read()
        
        # Fixtures Message
        with open(upcoming_fixtures_template_file, 'r') as file:
            upcoming_fixtures_message_body = file.read()
            upcoming_fixtures_message_body = upcoming_fixtures_message_body.replace('[GW]', str(self.gw))
            upcoming_fixtures_message_body = upcoming_fixtures_message_body.replace('[DEADLINE]', self.deadline)
            upcoming_fixtures_message_body += "\n"

            # append fixtures
            for f in self.fixtures:
                upcoming_fixtures_message_body += f"\n{f['fixture_id']}: {teams[f['team_h']]} X - X {teams[f['team_a']]}"

        # query participants
        query = ("SELECT * FROM participants;")
        participants = self.read_query(query)

        # Send Messages
        for participant in participants:

            print(f"Participant: {participant['participant_id']}")
            to_name = participant['first_name']
            to_number = participant['phone']

            # Welcome Message
            custom_welcome_back_message_body = welcome_back_message_body.replace('[NAME]', to_name)
            self.send_message(to_number, custom_welcome_back_message_body)

            # Fixtures Message
            custom_upcoming_fixtures_message_body = upcoming_fixtures_message_body.replace('[NAME]', to_name)
            self.send_message(to_number, custom_upcoming_fixtures_message_body)


if __name__ == "__main__":
    
    Action = InitialMessage()
    
    # if there is an upcoming gameweek, and message hasn't already been sent
    if Action.gw_soon and not Action.message_sent_prior:
        
        # insert fixtures - mysql
        Action.insert_fixtures()        
        # send message
        Action.send_fixtures_message()

        # schedule jobs for receiving messages, scoring, summary message etc
        # trigger via Cloudwatch
