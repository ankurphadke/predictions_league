from __future__ import print_function
from datetime import date, datetime, timedelta
import mysql.connector
import json
import sys
import os
import configparser

# access to parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(parent_dir)

from premier_league import PL

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('../params.cfg')


cnx = mysql.connector.connect(host = parser.get('mysql', 'host'),
                              user = parser.get('mysql', 'user'),
                              password = parser.get('mysql', 'password'),
                              database = parser.get('mysql', 'database'))
cursor = cnx.cursor()

def insert_team_names():
    pl = PL()
    teams = pl.get_teams()

    add_teams = ("INSERT INTO teams "
                 "(team_id, team_name) "
                 "VALUES (%s, %s)")

    for t_id, t_name in teams.items():
        t = (t_id, t_name)
        try:
            cursor.execute(add_teams, t)
            print(f"Inserted Team: {t}")
        except:
            print(f"Failed to Insert Team: {t}")

def register_participants():

    # read data from json
    with open('participants.json') as json_file:

        add_participant = ("INSERT INTO participants "
                            "(first_name, phone, admin) "
                            "VALUES (%(first_name)s, %(phone)s, %(admin)s)")

        for line in json_file:
            participant = json.loads(line)

            try:
                cursor.execute(add_participant, participant)
                print(f"Inserted Participant: {participant}")
            except:
                print(f"Failed to Insert Participant: {participant}")

insert_team_names()
register_participants()

cnx.commit()
cursor.close()
cnx.close()