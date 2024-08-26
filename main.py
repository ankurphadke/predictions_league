import configparser
from datetime import datetime, timezone, timedelta
import pandas as pd

import DatabaseLib as DB
import EmailLib as Email
import FormLib as Form
import PremierLeagueLib as PL

config = configparser.ConfigParser()
config.read( "params.cfg" )

CORRECT_GD_PTS = 1
CORRECT_OUTCOME_PTS = 1
CORRECT_SCORE_PTS = 2
FROM_EMAIL = config[ "email" ][ "from_address" ]
TIME_HORIZON = 72

class FormError( Exception ):
    pass

class GameweekError( Exception ):
    pass

class EmailError( Exception ):
    pass

# Returns upcoming gameweek information if it has not yet been processed.
def new_gameweek():
    upcoming = PL.get_upcoming_fixtures( TIME_HORIZON )
    if not upcoming:
        raise GameweekError( f"No gameweek in next { TIME_HORIZON } hours" )
    gw = upcoming[ 0 ]
    deadline = upcoming[ 1 ]
    fixtures = upcoming[ 2 ]

    query = f"SELECT * FROM gameweek WHERE id={ gw };"
    rows = DB.read_query(query)
    if len( rows ) > 0:
        raise GameweekError( ( f"Fixtures for gameweek { gw } have already"
                                " been updated" ) )

    query = f"SELECT * FROM form WHERE gw={ gw };"
    rows = DB.read_query(query)
    if len( rows ) > 0:
        raise GameweekError( ( f"Prediction form for gameweek { gw } has"
                                " already been sent" ) )

    return gw, deadline, fixtures

# Gets fixture results if all games in the current gameweek have ended.
def complete_gameweek( gw ):
    query = f"SELECT MAX(gw) as last_updated_gw from leaderboard;"
    last_updated_gw = DB.read_query( query )[ 0 ][ "last_updated_gw" ]
    print( f"Last update: GW { last_updated_gw } results" )
    if gw == last_updated_gw:
        raise GameweekError( f"GW { gw } results have already been updated" )

    results = PL.get_results( gw )
    for r in results:
        if r[ 'finished_provisional' ] == False:
            raise GameweekError( ( f"Fixture { r[ 'id' ] } from"
                                   f" GW { gw } has not yet finished." ) )
    result_data = []
    for r in results:
        row = {
            "fixture_id":   r[ "id" ],
            "team_h_score": r[ "team_h_score" ],
            "team_a_score": r[ "team_a_score" ],
        }
        result_data.append( row )
    DB.write_insert( 'result', result_data )
    return result_data

def process_responses( gw ):
    query = f"SELECT * FROM form WHERE gw={ gw };"
    forms = DB.read_query( query )
    if len( forms ) == 0:
        raise FormError( f"Form for GW { gw } cannot be found." )
    if len( forms ) > 1:
        raise FormError( f"Multiple forms found for GW { gw }." )
    form_id = forms[ 0 ][ "id" ]
    questions = Form.get_questions( form_id )

    name_q_id = next(
        ( k for k, v in questions.items() if v == "What is your name?" ),
        None
    )
    del questions[ name_q_id ]
    responses = Form.get_responses( form_id )

    query = f"SELECT id, first_name FROM user;"
    users = DB.read_query( query )
    predictions = {
        user[ "id" ]: {
            "submission_time": None,
            "answers":         None,
        }
        for user in users
    }
    users_dict = { u[ "first_name" ]: u[ "id" ] for u in users }

    query = f"SELECT deadline_time FROM gameweek where id={ gw };"
    deadline_time = DB.read_query( query )[ 0 ][ "deadline_time" ] + ":00"

    for r in responses:
        first_name = r[ "answers" ][ name_q_id ][ "textAnswers" ][ "answers" ]\
                        [ 0 ][ "value" ]
        user_id = users_dict[ first_name ]
        submission_time = str(
            datetime.strptime(
                r[ "lastSubmittedTime" ],
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace( tzinfo=timezone.utc )
        )[ :19 ]
        if submission_time >= deadline_time:
            continue
        if predictions[ user_id ][ "submission_time" ] is None or \
            submission_time > predictions[ user_id ][ "submission_time" ]:
            predictions[ user_id ][ "submission_time" ] = submission_time
            predictions[ user_id ][ "answers" ] = r[ "answers" ]

    query = f"SELECT * FROM fixture WHERE gw={ gw };"
    fixtures = DB.read_query( query )
    prediction_data = []
    for user_id in predictions:
        if predictions[ user_id ][ "submission_time" ] is None:
            # The user did not submit their predictions.
            continue
        for fixture in fixtures:
            h_q_id = next(
                ( k for k, v in questions.items() if v.split( '(')[ 1 ][ :-1 ] \
                    == str( fixture[ "id" ] ) + "H" ),
                None
            )
            a_q_id = next(
                ( k for k, v in questions.items() if v.split( '(')[ 1 ][ :-1 ] \
                    == str( fixture[ "id" ] ) + "A" ),
                None
            )
            prediction = {
                "user_id":         user_id,
                "fixture_id":      fixture[ "id" ],
                "prediction_time": predictions[ user_id ][ "submission_time" ],
                "team_h_pred":     int(
                    predictions[ user_id ][ "answers" ][ h_q_id ]\
                        [ "textAnswers" ][ "answers" ][ 0 ][ "value" ]
                ),
                "team_a_pred":     int(
                    predictions[ user_id ][ "answers" ][ a_q_id ]\
                        [ "textAnswers" ][ "answers" ][ 0 ][ "value" ]
                ),
            }
            prediction_data.append( prediction )
    DB.write_insert( 'prediction', prediction_data )
    return prediction_data

def score_responses( gw, result_data, prediction_data ):
    results = {
        r[ "fixture_id" ]: {
            "team_h": r[ "team_h_score" ],
            "team_a": r[ "team_a_score" ],
        }
        for r in result_data
    }
    fixture_score_data = []
    for p in prediction_data:
        team_h_actual = results[ p[ "fixture_id" ] ][ "team_h" ]
        team_a_actual = results[ p[ "fixture_id" ] ][ "team_a" ]
        gd_actual = team_h_actual - team_a_actual
        outcome_actual = 0 if gd_actual == 0 else gd_actual // abs( gd_actual )
        team_h_pred = p[ "team_h_pred" ]
        team_a_pred = p[ "team_a_pred" ]
        gd_pred = team_h_pred - team_a_pred
        outcome_pred = 0 if gd_pred == 0 else gd_pred // abs( gd_pred )
        correct_score = ( ( team_h_actual == team_h_pred ) and
                          ( team_a_actual == team_a_pred ) )
        correct_outcome = ( outcome_actual == outcome_pred )
        correct_gd = ( gd_actual == gd_pred )
        points = ( ( correct_score * CORRECT_SCORE_PTS ) +
                   ( correct_outcome * CORRECT_OUTCOME_PTS ) +
                   ( correct_gd * CORRECT_GD_PTS ) )
        fixture_score = {
            "user_id": p[ "user_id" ],
            "fixture_id": p[ "fixture_id" ],
            "correct_score": correct_score,
            "correct_outcome": correct_outcome,
            "correct_gd": correct_gd,
            "points": points,
        }
        fixture_score_data.append( fixture_score )
    DB.write_insert( 'fixture_score', fixture_score_data )

    query = f"SELECT * FROM user;"
    users = { u[ "id" ] for u in DB.read_query(query) }
    gameweek_total = {}
    for f in fixture_score_data:
        if f[ "user_id" ] not in gameweek_total:
            gameweek_total[ f[ "user_id" ] ] = 0
        gameweek_total[ f[ "user_id" ] ] += f[ "points" ]
    min_points = 0
    if len( gameweek_total ) > 0:
        min_points = min( gameweek_total.values() )
    gameweek_score_data = []
    for user_id in users:
        if user_id in gameweek_total:
            gameweek_score = {
                "user_id": user_id,
                "gw": gw,
                "missed_gw": False,
                "total_points": gameweek_total[ user_id ],
            }
            gameweek_score_data.append( gameweek_score )
        else:
            # This user did not submit predictions for this gw, so we assign
            # min_points to the user for this gw.
            gameweek_score = {
                "user_id": user_id,
                "gw": gw,
                "missed_gw": True,
                "total_points": min_points,
            }
            gameweek_score_data.append( gameweek_score )
    DB.write_insert( 'gameweek_score', gameweek_score_data )
    return gameweek_score_data

def update_leaderboard( gw, gameweek_score_data ):
    query = f"SELECT * FROM leaderboard;"
    leaderboard_data = DB.read_query(query)
    gameweek_scores = {
        gs[ "user_id" ]: {
            "gw": gs[ "gw" ],
            "total_points": gs[ "total_points" ],
        }
        for gs in gameweek_score_data
    }
    for row in leaderboard_data:
        if row[ "gw" ] != gameweek_scores[ row[ "user_id" ] ][ "gw" ] - 1:
            raise GameweekError(
                str( f"Last leaderboard update was for GW { row[ "gw" ] }, and"
                     f" attempting invalid update for GW"
                     f" { gameweek_scores[ row[ "user_id" ] ][ "gw" ] }" )
            )
        if gw != gameweek_scores[ row[ "user_id" ] ][ "gw" ]:
            raise GameweekError(
                str( f"Attempting an invalid leaderboard update for GW"
                     f"{ gameweek_scores[ row[ "user_id" ] ][ "gw" ] }" )
            )
        row[ "total_points" ] += \
            gameweek_scores[ row[ "user_id" ] ][ "total_points" ]
        row[ "gw" ] = gameweek_scores[ row[ "user_id" ] ][ "gw" ]
    DB.write_insert( 'leaderboard', leaderboard_data, replace=True )
    return leaderboard_data

def get_form( gw, deadline, fixtures ):
    query = f"SELECT * FROM form WHERE gw={ gw };"
    rows = DB.read_query(query)
    if len( rows ) > 0:
        raise FormError( ( f"Prediction form for gameweek { gw } already"
                            " exists" ) )

    query = f"SELECT * FROM team"
    rows = DB.read_query(query)
    teams = { row[ "id" ]: row[ "name" ] for row in rows }
    form_fixtures = [
        {
            "id": f[ "id" ],
            "kickoff_time": f[ "kickoff_time" ],
            "team_h": teams[ f[ "team_h" ] ],
            "team_a": teams[ f[ "team_a" ] ],
        }
        for f in fixtures
    ]
    query = f"SELECT * FROM user"
    users = DB.read_query(query)
    form_id, responder_uri = Form.create_form( gw, deadline, form_fixtures,
                                               users )
    form_data = [ {
        "id":               form_id,
        "gw":               gw,
        "responder_uri":    responder_uri,
    } ]
    DB.write_insert( 'form', form_data )
    return form_id, responder_uri

def summarize_results( gw, users, teams, result_data, prediction_data,
                       gameweek_score_data ):
    if len( users ) == 0:
        raise EmailError( ( f"No users registered for predictions league" ) )
    query = f"SELECT * FROM fixture WHERE gw={ gw }"
    fixtures = DB.read_query(query)
    users_dict = { u[ "id" ]: u[ "first_name" ] for u in users }
    fixtures_dict = { f[ "id" ]: \
                        f"{ teams[ f[ "team_h" ] ] }-{ teams[ f[ "team_a" ] ] }"
                      for f in fixtures }
    results_dict = { r[ "fixture_id" ]: \
                        f"{ r[ "team_h_score" ] }-{ r[ "team_a_score" ] }"
                     for r in result_data }

    summary = {
        u[ "first_name" ]: {
            fixtures_dict[ f[ "id" ] ]: ""
            for f in fixtures
        }
        for u in users
    }
    assert len( users )==len( gameweek_score_data )
    for gs in gameweek_score_data:
        summary[ users_dict[ gs[ "user_id" ] ] ][ "Total Points" ] = \
            gs[ "total_points" ]
    summary[ "Result" ] = {
        fixtures_dict[ f[ "id" ] ]: results_dict[ f[ "id" ] ]
        for f in fixtures
    }
    summary[ "Result" ][ "Total Points" ] = ""
    for p in prediction_data:
        first_name = users_dict[ p[ "user_id" ] ]
        fixture_title = fixtures_dict[ p[ "fixture_id" ] ]
        assert first_name in summary
        assert fixture_title in summary[ first_name ]
        summary[ first_name ][ fixture_title ] = \
            f"{ p[ "team_h_pred" ] }-{ p[ "team_a_pred" ] }"

    results_summary = pd.DataFrame( summary )
    return results_summary

def draft_email( users, gw, deadline, responder_uri, results_summary,
                 leaderboard_data ):
    if len( users ) == 0:
        raise EmailError( ( f"No users registered for predictions league" ) )

    to_addresses = [ u[ "email" ] for u in users ]
    from_address = FROM_EMAIL
    subject = f"Footy Mates PL Predictions - GW { gw }"
    body = (
        "Hi all,\n\n"
        f"Kindly submit your predictions for Premier League GW { gw }.\n\n"
        f"Submission deadline: { deadline } UTC.\n"
        f"Google Form: { responder_uri }\n\n"
        "Good luck!"
    )

    if results_summary is not None:
        body += str(
            "\n\n"
            f"GW { gw } Predictions:\n"
            f"{ results_summary.to_string(index=False) }"
        )

    if leaderboard_data:
        user_first_names = {
            u[ "id" ]: u[ "first_name" ]
            for u in users
        }
        leaderboard_data.sort( key = lambda x: x[ "total_points" ],
                               reverse=True )
        leaderboard = ""
        position = 0
        for lr in leaderboard_data:
            position += 1
            user_position = str(
                f"\t{ position }. "
                f"{ user_first_names[ lr[ "user_id" ] ] } "
                f"- { lr[ "total_points" ] } pts"
            )
            leaderboard += user_position + "\n"
        body += str(
            "\n\n"
            f"Points table after GW { gw - 1 }:\n"
            f"{ leaderboard }"
        )
    return to_addresses, from_address, subject, body

if __name__ == "__main__":

    gw, deadline, fixtures = new_gameweek()

    query = f"SELECT * FROM user;"
    users = DB.read_query(query)
    query = f"SELECT * FROM team;"
    teams = { t[ "id" ]: t[ "name" ] for t in DB.read_query(query) }
    prediction_data, gameweek_score_data, leaderboard_data, results_summary = \
        None, None, None, None

    if gw > 1:
        result_data = complete_gameweek( gw-1 )
        prediction_data = process_responses( gw-1 )
        gameweek_score_data = score_responses( gw-1, result_data,
                                               prediction_data )
        leaderboard_data = update_leaderboard( gw-1, gameweek_score_data )
        results_summary = summarize_results( gw-1, users, teams, result_data,
                                             prediction_data,
                                             gameweek_score_data )

    gameweek_data = [ {
        "id":               gw,
        "deadline_time":    deadline
    } ]
    DB.write_insert( 'gameweek', gameweek_data )
    DB.write_insert( 'fixture', fixtures )

    form_id, responder_uri = get_form( gw, deadline, fixtures )
    print( f"\nPrediction Form: { responder_uri }\n" )

    to_addresses, from_address, subject, body = \
        draft_email( users, gw, deadline, responder_uri, results_summary,
                     leaderboard_data )
    Email.send_email( to_addresses, from_address, subject, body )
