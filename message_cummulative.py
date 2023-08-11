### Cummulate Predictions
### Send to Admins

import configparser
from datetime import datetime, timezone

from event import Event

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')

send_within_hrs_after_deadline=int(parser.get('rules','send_within_hrs_after_deadline'))

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
                 "ON f.team_a=t2.team_id;")
        fixtures = self.read_query(query)

        query = (f"SELECT f.fixture_id, p.participant_id, pr.first_name, p.team_h_pred, p.team_a_pred "
                 f"FROM predictions p "
                 f"LEFT JOIN fixtures f "
                 f"ON p.fixture_id=f.fixture_id "
                 f"LEFT JOIN participants pr "
                 f"ON p.participant_id=pr.participant_id;")
        predictions = self.read_query(query)

        for f in fixtures:
            
            # filter by fixture
            pps = [pred for pred in predictions if pred['fixture_id']==f['fixture_id']]

            MESSAGE += f"\n\n{f['team_h']} vs {f['team_a']}"

            for pp in pps:
                MESSAGE += f"\n  {pp['first_name']}: {pp['team_h_pred']} - {pp['team_a_pred']}"

        return MESSAGE
    
    def send_cummulative(self, message_body):

        # only send to admins?
        query = ("SELECT * FROM participants;")
        participants = self.read_query(query)

        for p in participants:
            print(p['first_name'])
            self.send_message(p['phone'], message_body)


if __name__ == "__main__":
    
    Action = CummulativeMessage()
    gw, hrs_past_deadline = Action.get_curr_gw()

    # after deadline and before deadline + hrs_past_deadline
    if 0 <= hrs_past_deadline <= send_within_hrs_after_deadline:
        message_body = Action.get_cummulative_predictions(gw)
        Action.send_cummulative(message_body)

    