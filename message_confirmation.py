### Triggered upon Message Reception (API Gateway, AWS Lambda)
### Authenticate Message
### DB Insert
### Send Confirmation Message

import os
import sys
from datetime import datetime

from event import Event
from premier_league import PL


class ConfirmationMessage(Event):

    def __init__(self, sid) -> None:

        super().__init__()

        # incoming message metadata
        self.sid = sid
        self.message = self.get_message(self.sid)
        self.message_body = self.message['body']
        self.message_from = self.message['from_']
        self.participant_phone = self.message['from_']
        self.message_time = datetime.strptime(str(self.message['date_created'])[:16], '%Y-%m-%d %H:%M')

        # prediction data stored here
        self.predictions = {}

    def authenticate_response(self):

        ## authenticate sender
        query = (f"SELECT * FROM participants WHERE phone={self.message_from};")
        participants = self.read_query(query)

        name_from_message = self.message_body.split(' ')[0][:-2]

        if len(participants)!=1 or participants[0]['first_name']!=name_from_message:

            # name doesn't match
            # admin can send predictions on behalf of others
            if len(participants)>0 and participants[0]['admin']==1:

                # if admin sender, treat as prediction on behalf of name_from_message (if valid)
                query = (f"SELECT * FROM participants WHERE first_name='{name_from_message}';")
                proxy_participant = self.read_query(query)

                if len(proxy_participant)!=0:
                    # replace admin phone number to participant being represented
                    self.participant_phone = proxy_participant[0]['phone']
                else:
                    return False, 'MissingUserError'
            else:
                return False, 'MissingUserError'

        ## authenticate prediction window open
        gw_from_message = int(self.message_body.split('Deadline')[0].split(': ')[-1])
        deadline_from_message = self.message_body.split(' UTC')[0].split('Deadline: ')[-1]
        
        query = (f"SELECT * FROM fixtures WHERE gw={gw_from_message};")
        fixtures = self.read_query(query)
        
        if len(fixtures)==0 or fixtures[0]['gw_deadline_time']!=deadline_from_message:
            return False, 'MissingDeadlineError'
        
        # convert deadline_from_message to datetime type
        deadline_time = datetime.strptime(deadline_from_message, '%Y-%m-%d %H:%M')
        # deadline and twilio time both in UTC
        if self.message_time >= deadline_time:
            return False, 'DeadlinePassedError'

        ## authenticate all predictions present
        prediction_lines = self.message_body.split('Fixtures:')[-1].split('\n')        

        for line in prediction_lines:
            # parse predictions
            if (': ' not in line) or (' - ' not in line):
                continue # skip extra lines

            fixture_id = int(line.split(':')[0])
            space_split = line.split(' ')
            if not space_split[2].isdigit() or not space_split[4].isdigit():
                continue

            # if digit > len 4 !!!!!!!!!!!!!!!!!!

            self.predictions[fixture_id] = {
                'team_h_name': space_split[1],
                'team_a_name': space_split[5],
                'team_h_pred': int(space_split[2]),
                'team_a_pred': int(space_split[4]),
            }

        # team_id: team_name mapping
        query = (f"SELECT * FROM teams;")
        teams_result = self.read_query(query)
        teams = {}
        for tr in teams_result:
            teams[tr['team_id']] = tr['team_name']

        for f in fixtures:

            if f['fixture_id'] not in self.predictions:
                return False, 'MissingPredictionError'

            if teams[f['team_h']]!=self.predictions[f['fixture_id']]['team_h_name'] or \
                teams[f['team_a']]!=self.predictions[f['fixture_id']]['team_a_name']:
                return False, 'IncorrectTeamError'

        # valid response
        return True, 'ValidResponse'
    

    def insert_predictions(self):

        # get participant_id
        query = (f"SELECT * FROM participants WHERE phone={self.participant_phone};")
        participant_id = self.read_query(query)[0]['participant_id']
        
        rows = []
        
        for fixture_id, data in self.predictions.items():
            pred = {
                'participant_id': participant_id,
                'fixture_id': fixture_id,
                'prediction_time': self.message_time,
                'team_h_pred': data['team_h_pred'],
                'team_a_pred': data['team_a_pred']
            }
            rows.append(pred)

        # insert into table, replaces predictions if user is updating them before deadline
        self.write_insert('predictions', rows, replace=True)


if __name__ == "__main__":

    # Triggered by Lambda upon Message Reception

    # Using message body for all authentication
    # not ideal/secure, change this going forward

    CONFIRMATION = ""

    # initialize class, message SID passed by Lambda
    message_sid = sys.argv[1]
    Action = ConfirmationMessage(message_sid)

    # authenticate message/prediction
    is_authentic, authentication_message = Action.authenticate_response()

    if is_authentic:
        # insert predictions - mysql
        Action.insert_predictions()

        CONFIRMATION += 'Thank you for sending in your predictions!'
        CONFIRMATION += ' '
        CONFIRMATION += 'You can update them before the deadline by resending them.'
        CONFIRMATION += '\n'
        CONFIRMATION += '\n'
        CONFIRMATION += 'Predictions will be scored after the gameweek ends.'
    else:
        CONFIRMATION += 'Your response is invalid: '
        CONFIRMATION += authentication_message
    
    # send message
    Action.send_message(Action.message_from, CONFIRMATION)

