import requests, json
from datetime import datetime, timezone, timedelta

class PL:

    def __init__(self) -> None:

        # base url for all FPL API endpoints
        self.base_url = 'https://fantasy.premierleague.com/api/'
        self.basic_path = 'bootstrap-static/'
        self.fixture_path = 'fixtures/'

    def get_teams(self):

        # get team data from bootstrap-statis endpoint
        basic_json = requests.get(self.base_url + self.basic_path).json()
        teams_json = basic_json['teams']
        # store code and short_name in a dictionary
        teams = {}
        for t in teams_json:
            teams[t['id']] = t['short_name']

        return teams

    def get_fixtures(self, gw):

        filters = f'?event={gw}'
        fixtures_full = requests.get(self.base_url + self.fixture_path + filters).json()

        # select attributes
        fixtures_short = [{'fixture_id': f['code'], 
                            'gw': gw, 
                            'kickoff_time': str(datetime.strptime(f['kickoff_time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc))[:16], 
                            'team_h': f['team_h'], 
                            'team_a': f['team_a']} for f in fixtures_full]

        return fixtures_short
    

    def get_results(self, gw):

        filters = f'?event={gw}'
        results_full = requests.get(self.base_url + self.fixture_path + filters).json()

        # select attributes
        results_short = [{'fixture_id': f['code'], 
                            'gw': gw, 
                            'kickoff_time': str(datetime.strptime(f['kickoff_time'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc))[:16], 
                            'finished': f['finished'], 
                            'finished_provisional': f['finished_provisional'], 
                            'team_h': f['team_h'], 
                            'team_a': f['team_a'],
                            'team_h_score': f['team_h_score'], 
                            'team_a_score': f['team_a_score']} for f in results_full]

        return results_short
         

    def get_upcoming_fixtures(self, send_hrs_prior_deadline):

        basic_json = requests.get(self.base_url + self.basic_path).json()
        gws_json = basic_json['events']

        for gw_info in gws_json:

            # gameweek deadline (UTC)
            deadline_str = gw_info['deadline_time']
            deadline_time = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            # add 30 mins since fpl deadline is 1h30m prior to kick-off, and get message friendly string
            prediction_deadline = str(deadline_time + timedelta(minutes=30))[:16]
            friendly_deadline = prediction_deadline + (' UTC')
            current_utc_time = datetime.now(timezone.utc)
            # calculate the time to deadline
            hrs_to_deadline = (deadline_time - current_utc_time).total_seconds() / 3600

            # if nearing deadline, return upcoming fixtures
            if 0 < hrs_to_deadline <= send_hrs_prior_deadline:
                
                gw = gw_info['id']
                
                # get fixtures
                fixtures = self.get_fixtures(gw)
                for f in fixtures:
                    f['gw_deadline_time'] = prediction_deadline

                return gw, friendly_deadline, fixtures
                
                # ignore future gws, next deadline will not be within 24 hrs (script schedule)

        return None
