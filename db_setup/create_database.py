from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode

import configparser

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('../params.cfg')

### Set Schema

DB_NAME = parser.get('mysql', 'database')

TABLES = {}
TABLES['participants'] = (
    "CREATE TABLE `participants` ("
    "  `participant_id` int(4) NOT NULL AUTO_INCREMENT,"
    "  `first_name` varchar(14) NOT NULL,"
    "  `phone` varchar(14) NOT NULL,"
    "  `admin` BIT NOT NULL,"
    "  PRIMARY KEY (`participant_id`), UNIQUE KEY `phone` (`phone`), UNIQUE KEY `first_name` (`first_name`)" # for proxy purposes, not ideal
    ")")

TABLES['teams'] = (
    "CREATE TABLE `teams` ("
    "  `team_id` int(4) NOT NULL,"
    "  `team_name` varchar(50) NOT NULL,"
    "  PRIMARY KEY (`team_id`)"
    ")")

TABLES['fixtures'] = (
    "CREATE TABLE `fixtures` ("
    "  `fixture_id` int(11) NOT NULL,"
    "  `gw` int(2) NOT NULL,"
    "  `gw_deadline_time` varchar(32) NOT NULL,"
    "  `kickoff_time` varchar(32) NOT NULL,"
    "  `team_h` int(4) NOT NULL,"
    "  `team_a` int(4) NOT NULL,"
    "  PRIMARY KEY (`fixture_id`),"
    "  FOREIGN KEY (`team_h`) REFERENCES `teams` (`team_id`),"
    "  FOREIGN KEY (`team_a`) REFERENCES `teams` (`team_id`)"
    ")")

TABLES['predictions'] = (
    "CREATE TABLE `predictions` ("
    "  `participant_id` int(4) NOT NULL,"
    "  `fixture_id` int(11) NOT NULL,"
    "  `prediction_time` varchar(32) NOT NULL,"
    "  `team_h_pred` int(4) NOT NULL,"
    "  `team_a_pred` int(4) NOT NULL,"
    "  PRIMARY KEY (`participant_id`, `fixture_id`),"
    "  FOREIGN KEY (`participant_id`) REFERENCES `participants` (`participant_id`),"
    "  FOREIGN KEY (`fixture_id`) REFERENCES `fixtures` (`fixture_id`)"
    ")")

TABLES['results'] = (
    "CREATE TABLE `results` ("
    "  `fixture_id` int(11) NOT NULL,"
    "  `team_h_score` int(4) NOT NULL,"
    "  `team_a_score` int(4) NOT NULL,"
    "  PRIMARY KEY (`fixture_id`),"
    "  FOREIGN KEY (`fixture_id`) REFERENCES `fixtures` (`fixture_id`)"
    ")")

TABLES['scores'] = (
    "CREATE TABLE `scores` ("
    "  `participant_id` int(4) NOT NULL,"
    "  `fixture_id` int(11) NOT NULL,"
    "  `correct_outcome` BIT NOT NULL,"
    "  `correct_score` BIT NOT NULL,"
    "  `points` int(2) NOT NULL,"
    "  PRIMARY KEY (`participant_id`, `fixture_id`),"
    "  FOREIGN KEY (`participant_id`) REFERENCES `participants` (`participant_id`),"
    "  FOREIGN KEY (`fixture_id`) REFERENCES `fixtures` (`fixture_id`)"
    ")")

TABLES['leaderboard'] = (
    "CREATE TABLE `leaderboard` ("
    "  `participant_id` int(4) NOT NULL,"
    "  `correct_outcomes` int(8) NOT NULL,"
    "  `correct_scores` int(8) NOT NULL,"
    "  `total_points` int(8) NOT NULL,"
    "  `last_update_gw` int(4) NOT NULL,"
    "  PRIMARY KEY (`participant_id`),"
    "  FOREIGN KEY (`participant_id`) REFERENCES `participants` (`participant_id`)"
    ")")


### Connect to DB Instance

cnx = mysql.connector.connect(host = parser.get('mysql', 'host'),
                              user = parser.get('mysql', 'user'),
                              password = parser.get('mysql', 'password'))
cursor = cnx.cursor()

### Create Database

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

try:
    cursor.execute("USE {}".format(DB_NAME))
except mysql.connector.Error as err:
    print("Database {} does not exists.".format(DB_NAME))
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        create_database(cursor)
        print("Database {} created successfully.".format(DB_NAME))
        cnx.database = DB_NAME
    else:
        print(err)
        exit(1)

### Create Tables

for table_name in TABLES:
    table_description = TABLES[table_name]
    try:
        print("Creating table {}: ".format(table_name), end='')
        cursor.execute(table_description)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")

cursor.close()
cnx.close()
