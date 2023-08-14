### Get Match Results
### Compute Scores
### DB Insert
### Send Summary Message
### Update Leaderboard

import sys
import configparser
import numpy as np

from event import Event
from premier_league import PL

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')

score_summary_template_file = parser.get('message_templates','score_summary')
leaderboard_template_file = parser.get('message_templates','leaderboard')

class FinalMessage(Event):

    def __init__(self, gw) -> None:

        super().__init__()
        self.gw = gw
        self.results = None
        self.scores = None
        self.summary = None

    
    def get_results(self):
        
        pl = PL()
        self.results = pl.get_results(self.gw)

    
    def authenticate_results(self):

        # consistency between fixtures and results
        query = (f"SELECT fixture_id FROM fixtures WHERE gw={self.gw};")
        fixtures = self.read_query(query)

        set_fixtures = {f['fixture_id'] for f in fixtures}
        set_results = {r['fixture_id'] for r in self.results}
        
        if set_fixtures!=set_results:
            raise Exception(f"Inconsistency between Fixtures and Results: GW {self.gw}")

        # ensure all matches finished
        # 'finished_provisional' tag vs 'finished' tag
        # 'finished_provisional' updated first, assuming match score doesn't change later, only fpl assists/bps/etc
        for r in self.results:
            if r['finished_provisional']==False:
                raise Exception(f"Match Incomplete: GW {self.gw}, Fixture {r['fixture_id']}")

    
    def insert_results(self):

        data = []

        for result in self.results:

            result_short = {
                'fixture_id': result['fixture_id'],
                'team_h_score': result['team_h_score'],
                'team_a_score': result['team_a_score']
            }

            data.append(result_short)

        self.write_insert('results', data)

    
    def calculate_scores(self):
        
        # query
        query = ("SELECT f.fixture_id, f.gw, p.participant_id, f.team_h, f.team_a, "
                        "th.team_name as team_h_name, ta.team_name as team_a_name, "
                        "p.team_h_pred, p.team_a_pred, r.team_h_score, r.team_a_score "
                 "FROM fixtures f "
                 "LEFT JOIN predictions p ON f.fixture_id=p.fixture_id "
                 "LEFT JOIN results r ON f.fixture_id=r.fixture_id "
                 "LEFT JOIN teams th ON f.team_h=th.team_id "
                 "LEFT JOIN teams ta ON f.team_a=ta.team_id;")
        scores = self.read_query(query)

        # compute scores
        for p in scores:

            correct_outcome = False
            correct_score = False
            points = 0

            # correct outcome (win/draw/loss)
            outcome = np.sign(p['team_h_score']-p['team_a_score'])
            pred_outcome = np.sign(p['team_h_pred']-p['team_a_pred'])
            if outcome==pred_outcome:
                correct_outcome=True
                points += 1
            
            # correct score (both)
            if p['team_h_score']==p['team_h_pred'] and p['team_a_score']==p['team_a_pred']:
                correct_score = True
                points += 2
            
            p['correct_outcome'] = correct_outcome
            p['correct_score'] = correct_score
            p['points'] = points

        self.scores = scores
        

    def insert_scores(self):
        
        data = []

        for s in self.scores:

            scores_short = {
                'participant_id': s['participant_id'],
                'fixture_id': s['fixture_id'],
                'correct_outcome': s['correct_outcome'],
                'correct_score': s['correct_score'],
                'points': s['points']
            }

            data.append(scores_short)

        self.write_insert('scores', data)


    def send_scores(self):

        template_file = open(score_summary_template_file, "r")
        template_text = template_file.read()
        
        query = ("SELECT * FROM participants")
        participants = self.read_query(query)

        scores = self.scores
        summary = []

        for p in participants:

            message_body = template_text
            message_body = message_body.replace("[NAME]", p['first_name']).replace("[GW]", str(self.gw))

            participant_summary = {
                "participant_id": p['participant_id'],
                "correct_outcomes": 0,
                "correct_scores": 0,
                "total_points": 0,
                "last_update_gw": self.gw
            }

            for s in scores:
                
                # filter by participant_id
                if s['participant_id']!=p['participant_id']:
                    continue

                message_body += "\n\n"
                message_body += f"{s['team_h_name']} - {s['team_a_name']}"
                message_body += "\n"
                message_body += f"Score: {s['team_h_score']}-{s['team_a_score']}"
                message_body += " "
                message_body += f"Pred: {s['team_h_pred']}-{s['team_a_pred']}"
                message_body += "\n"
                message_body += f"Points: {s['points']}"

                participant_summary['correct_outcomes'] += int(s['correct_outcome'])
                participant_summary['correct_scores'] += int(s['correct_score'])
                participant_summary['total_points'] += s['points']

            message_body += "\n\n"
            message_body += f"Correct Outcomes: {participant_summary['correct_outcomes']}"
            message_body += "\n"
            message_body += f"Correct Scores: {participant_summary['correct_scores']}"
            message_body += "\n"
            message_body += f"Total Points: {participant_summary['total_points']}"

            summary.append(participant_summary)

            # send message
            self.send_message(p['phone'], message_body)

        self.summary = summary


    def update_leaderboard(self):

        summary = self.summary

        query = ("SELECT * FROM leaderboard")
        leaderboard = self.read_query(query)

        # ensure not double update
        if len(leaderboard)!=0 and leaderboard[0]['last_update_gw']==self.gw:
            raise Exception(f"Attempting Leaderboard Double Update")

        if self.gw==1:
            self.write_insert('leaderboard', summary, replace=True)
        else:
            # leaderboard missing
            if len(leaderboard)==0:
                raise Exception(f"Leaderboard Doesn't Exist")

            # create indexed summary
            indexed_summary = {}
            for s in summary:
                p = s['participant_id']
                indexed_summary[p] = s

            new_leaderboard = []
            for l in leaderboard:
                s = indexed_summary[l['participant_id']]
                l['correct_outcomes'] += s['correct_outcomes']
                l['correct_scores'] += s['correct_scores']
                l['total_points'] += s['total_points']
                l['last_update_gw'] = s['last_update_gw']
                
                new_leaderboard.append(l)
            
            # update leaderboard
            self.write_insert('leaderboard', new_leaderboard, replace=True)


    def send_leaderboard(self):

        template_file = open(leaderboard_template_file, "r")
        message_body = template_file.read()
        message_body = message_body.replace("[GW]", str(self.gw))

        query = ("SELECT * FROM leaderboard l "
                 "LEFT JOIN participants p ON l.participant_id=p.participant_id "
                 "ORDER BY l.total_points DESC")
        leaderboard = self.read_query(query)

        # confirm gw
        if self.gw!=leaderboard[0]['last_update_gw']:
            raise Exception(f"GW Inconsistency in Leaderboard")

        rank = 0
        for l in leaderboard:
            rank += 1
            message_body += "\n"
            message_body += f"{rank}. {l['first_name']} - {l['total_points']} - ({l['correct_outcomes']}, {l['correct_scores']})"

        query = ("SELECT * FROM participants")
        participants = self.read_query(query)

        for p in participants:
        
            self.send_message(p['phone'], message_body)


if __name__ == "__main__":

    gw = int(sys.argv[1])
    
    Action = FinalMessage(gw)

    Action.get_results()
    Action.authenticate_results()
    Action.insert_results()

    Action.calculate_scores()
    Action.insert_scores()
    Action.send_scores()

    Action.update_leaderboard()
    Action.send_leaderboard()
    
    # Empty Tables
    # - results
    # - scores
    # - leaderboard