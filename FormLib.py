from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools

CLIENT_SECRETS = "client_secrets.json"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
FORM_SCOPE = "https://www.googleapis.com/auth/forms.body"
RESPONSE_SCOPE = "https://www.googleapis.com/auth/forms.responses.readonly"
FORM_TOKEN = "token_form.json"
RESPONSE_TOKEN = "token_response.json"

def bold_text( text ):
    # TODO: Figure out bolding (tried html and special char without any success)
    return text

def create_form( gw, deadline, fixtures, users ):
    store = file.Storage( FORM_TOKEN )
    creds = None
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets( CLIENT_SECRETS, FORM_SCOPE )
        creds = tools.run_flow( flow, store )
    form_service = discovery.build(
        "forms",
        "v1",
        http=creds.authorize( Http() ),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    # TODO: Set document title and description
    title = f"Footy Mates PL Predictions - GW { gw }"
    description = ""
    FORM = {
        "info": {
            "title": title,
            # "documentTitle": title,
            # "description": description,
        }
    }
    user_options = [ { "value": u[ "first_name" ] } for u in users ]
    QUESTIONS = {
        "requests": [
            {
                "createItem": {
                    "item": {
                        "title": "What is your name?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "DROP_DOWN",
                                    "options": user_options,
                                }
                            }
                        },
                    },
                    "location": { "index": 0 },
                }
            }
        ]
    }
    for f in fixtures:
        questions = [
            ( f"{ bold_text( f[ "team_h" ] ) } vs"
              f" { bold_text( f[ "team_a" ] ) }:"
              f" Goals scored by { bold_text( f[ "team_h" ] ) }"
              f" ({ f[ "id" ] }H)" ),
            ( f"{ bold_text( f[ "team_h" ] ) } vs"
              f" { bold_text( f[ "team_a" ] ) }:"
              f" Goals scored by { bold_text( f[ "team_a" ] ) }"
              f" ({ f[ "id" ] }A)" ),
        ]
        for q in questions:
            request = {
                "createItem": {
                    "item": {
                        "title": q,
                        "questionItem": {
                            "question": {
                                "required": True,
                                "scaleQuestion": {
                                    "low": 0,
                                    "high": 10,
                                }
                            }
                        },
                    },
                    "location": { "index": 0 },
                }
            }
            QUESTIONS[ "requests" ].append( request )
    QUESTIONS[ "requests" ].reverse()
    result = form_service.forms().create( body=FORM ).execute()
    question_setting = (
        form_service.forms()
        .batchUpdate( formId=result[ "formId" ], body=QUESTIONS )
        .execute()
    )
    get_result = form_service.forms().get( formId=result[ "formId" ] ).execute()
    return get_result[ "formId" ], get_result[ "responderUri" ]

def get_questions( form_id ):
    store = file.Storage( FORM_TOKEN )
    creds = None
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets( CLIENT_SECRETS, FORM_SCOPE )
        creds = tools.run_flow( flow, store )
    form_service = discovery.build(
        "forms",
        "v1",
        http=creds.authorize( Http() ),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    form_metadata = form_service.forms().get( formId=form_id ).execute()
    questions = {}
    for item in form_metadata[ "items" ]:
        question_id = item[ "questionItem" ][ "question" ][ "questionId" ]
        question_text = item[ "title" ]
        questions[ question_id ] = question_text
    return questions

def get_responses( form_id ):
    store = file.Storage( RESPONSE_TOKEN )
    creds = None
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets( CLIENT_SECRETS, RESPONSE_SCOPE )
        creds = tools.run_flow( flow, store )
    form_service = discovery.build(
        "forms",
        "v1",
        http=creds.authorize( Http() ),
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    get_result = form_service.forms().responses().list( formId=form_id )\
                                                 .execute()
    responses = get_result[ "responses" ]
    return responses
