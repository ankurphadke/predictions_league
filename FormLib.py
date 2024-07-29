import requests

ENDPOINT_URL = "https://forms.googleapis.com"

def create_form( gw, fixtures ):

    CREATE_URL = ENDPOINT_URL + "/v1/forms"
    headers = {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN",  # Replace with your OAuth 2.0 access token
        "Content-Type": "application/json"
    }
    data = {
        "title": "My New Form",  # The title of the form
        "description": "This is a description for the form"
        # Add any other fields required by the API
    }
    response = requests.post( CREATE_URL, headers=headers, json=data )

    return form_id, form_url

def get_responses( form_id ):

    responses = None

    return responses
