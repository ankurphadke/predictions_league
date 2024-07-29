from datetime import datetime, timezone, timedelta
import requests

ENDPOINT_URL = "https://fantasy.premierleague.com/api/"
STATIC_PATH = "bootstrap-static/"
FIXTURES_PATH = "fxtures/"

def get_teams():

    response = requests.get( ENDPOINT_URL + STATIC_PATH ).json()
    teams_json = response[ "teams" ]
    teams = {}
    for team in teams_json:
        teams[ team[ "id" ] ] = team[ "short_name" ]

    return teams

def get_fixtures( gw ):

    filters = f"?event={ gw }"
    fixtures_full = requests.get( ENDPOINT_URL + FIXTURES_PATH + filters )\
                            .json()
    fixtures_short = [
        {
            "id"           : f[ "code" ],
            "gw"           : gw,
            "kickoff_time" : str(
                                datetime.strptime( f[ "kickoff_time" ],
                                                    "%Y-%m-%dT%H:%M:%SZ" )\
                                        .replace( tzinfo=timezone.utc )
                                )[ :16 ],
            "team_h"       : f[ "team_h" ],
            "team_a"       : f[ "team_a" ],
        }
        for f in fixtures_full
    ]

    return fixtures_short

def get_results( gw ):

    filters = f"?event={ gw }"
    results_full = requests.get( ENDPOINT_URL + FIXTURES_PATH + filters )\
                            .json()
    results_short = [
        {
            "id"           : f[ "code" ],
            "gw"                   : gw,
            "kickoff_time"         : str(
                                        datetime.strptime(
                                            f[ "kickoff_time" ],
                                            "%Y-%m-%dT%H:%M:%SZ" )\
                                        .replace( tzinfo=timezone.utc )
                                        )[ :16 ],
            "finished"             : f[ "finished" ],
            "finished_provisional" : f[ "finished_provisional" ],
            "team_h"               : f[ "team_h" ],
            "team_a"               : f[ "team_a" ],
            "team_h_score"         : f[ "team_h_score" ],
            "team_a_score"         : f[ "team_a_score" ]
        }
        for f in results_full
    ]

    return results_short

def get_upcoming_fixtures( send_hrs_prior_deadline ):

    response = requests.get( ENDPOINT_URL + STATIC_PATH ).json()
    gws_json = response[ "events" ]

    for gw_info in gws_json:

        # Gameweek deadline (UTC)
        # Add 30 mins since fpl deadline is 1h30m prior to kick-off
        deadline_str = gw_info[ "deadline_time" ]
        deadline_time = datetime.strptime( deadline_str,
                                            "%Y-%m-%dT%H:%M:%SZ" )\
                                            .replace( tzinfo=timezone.utc )
        prediction_deadline = str( deadline_time + timedelta(minutes=30) )\
                                [:16]
        friendly_deadline = prediction_deadline + ( " UTC" )
        current_utc_time = datetime.now( timezone.utc )
        hrs_to_deadline = ( deadline_time - current_utc_time )\
                            .total_seconds()\
                            / 3600

        # Ff in the past, skip
        if 0 < hrs_to_deadline:
            print( f"Next deadline: GW { gw_info[ "id" ] } -"
                    f" { str( deadline_time )[ :19 ] } -"
                    f" { round( hrs_to_deadline,1 ) } hrs to go" )
        else:
            continue

        # If nearing deadline, return upcoming fixtures, else, break
        if 0 < hrs_to_deadline <= send_hrs_prior_deadline:
            gw = gw_info[ "id" ]
            fixtures = self.get_fixtures( gw )
            for f in fixtures:
                f[ "gw_deadline_time" ] = prediction_deadline
            return gw, friendly_deadline, fixtures
        else:
            break

    return None
