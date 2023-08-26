### Execute after deadline has passed
### Schedule when prediction messages sent

### Cummulate Predictions
### Send to Admins

import configparser
import sys
from datetime import datetime, timezone

from event import Event

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')

CHAR_LIMIT = int(parser.get('twilio','CHAR_LIMIT'))

class CummulativeMessage(Event):

    def __init__(self) -> None:

        super().__init__()

    def get_curr_gw(self):

        query = ("SELECT gw, gw_deadline_time FROM fixtures ORDER BY gw DESC;")
        fixtures = self.read_query(query)
        gw, deadline_str = fixtures[0]['gw'], fixtures[0]['gw_deadline_time']
        deadline_time = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)

        current_utc_time = datetime.now(timezone.utc)
        hrs_past_deadline = (current_utc_time - deadline_time).total_seconds() / 3600

        return gw, hrs_past_deadline

    def get_cummulative_predictions(self, gw):

        MESSAGE = f"The deadline for GW {gw} PL Predictions has passed.\n"
        MESSAGE += f"\nGOOD LUCK!\n"
        MESSAGE += f"\nHere's what everyone predicted:"

        query = ("SELECT f.fixture_id, f.kickoff_time, t1.team_name as team_h, t2.team_name as team_a FROM fixtures f "
                 "LEFT JOIN teams t1 "
                 "ON f.team_h=t1.team_id "
                 "LEFT JOIN teams t2 "
                 "ON f.team_a=t2.team_id "
                 f"WHERE f.gw={gw} "
                 "ORDER BY f.kickoff_time;")
        fixtures = self.read_query(query)

        query = (f"SELECT f.fixture_id, p.participant_id, pr.first_name, p.team_h_pred, p.team_a_pred "
                 f"FROM predictions p "
                 f"LEFT JOIN fixtures f "
                 f"ON p.fixture_id=f.fixture_id "
                 f"LEFT JOIN participants pr "
                 f"ON p.participant_id=pr.participant_id "
                 f"WHERE f.gw={gw};")
        predictions = self.read_query(query)

        for f in fixtures:
            
            # filter by fixture
            pps = [pred for pred in predictions if pred['fixture_id']==f['fixture_id']]

            MESSAGE += f"\n\n{f['team_h']} vs {f['team_a']}"

            for pp in pps:
                MESSAGE += f"\n  {pp['first_name']}: {pp['team_h_pred']} - {pp['team_a_pred']}"

        return MESSAGE
    
    def send_cummulative(self, message_body):

        # only send to admins
        query = ("SELECT * FROM participants WHERE admin=1;")
        participants = self.read_query(query)

        # # separate message body into multiple messages due to Twilio char limit
        # delimiter = '\n\n'
        # parts = message_body.split(delimiter)
        
        # curr_message = ''
        # curr_part = 0
        # while curr_part < len(parts):
        #     # each iteration -> a message
        #     while len(curr_message)+len(parts[curr_part]) < CHAR_LIMIT:
        #         curr_message += parts[curr_part] + delimiter
        #         curr_part += 1
        #         if curr_part == len(parts):
        #             break

        #     print(curr_message)
        #     print('---')
        #     curr_message = ''

        for p in participants:
            print(p['first_name'])
            self.send_message(p['phone'], message_body)


if __name__ == "__main__":
    
    Action = CummulativeMessage()
    # from mysql fixtures, get latest gw
    # if a fixture is in this table, prediction messages for this fixture have been sent
    gw_db, hrs_past_deadline = Action.get_curr_gw()
    # Provide gw as a command argument instead?

    # confirm that it's the same gw
    gw_arg = int(sys.argv[1])
    # ensure that deadline has passed
    if gw_arg==gw_db and 0 <= hrs_past_deadline:
        message_body = Action.get_cummulative_predictions(gw_arg)
        Action.send_cummulative(message_body)
    else:
        print(f"Deadline for GW {gw_arg} hasn't yet passed")

    