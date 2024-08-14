-- Database schema

CREATE DATABASE predictions_league;

USE predictions_league;

CREATE TABLE user (
    id int(32) NOT NULL AUTO_INCREMENT,
    first_name varchar(32) NOT NULL,
    last_name varchar(32),
    email varchar(256) NOT NULL,
    admin BIT(1) DEFAULT b'0',
    PRIMARY KEY (id),
    UNIQUE KEY email (email)
);

CREATE TABLE team (
    id int(8) NOT NULL,
    name varchar(64) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE gameweek (
    id int(8) NOT NULL,
    deadline_time varchar(32) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE fixture (
    id int(32) NOT NULL,
    gw int(8) NOT NULL,
    kickoff_time varchar(32) NOT NULL,
    team_h int(8) NOT NULL,
    team_a int(8) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (gw) REFERENCES gameweek (id),
    FOREIGN KEY (team_h) REFERENCES team (id),
    FOREIGN KEY (team_a) REFERENCES team (id)
);

CREATE TABLE form (
    id varchar(256) NOT NULL,
    gw int(8) NOT NULL,
    responder_uri varchar(512),
    PRIMARY KEY (id),
    FOREIGN KEY (gw) REFERENCES gameweek (id)
);

CREATE TABLE prediction (
    user_id int(32) NOT NULL,
    fixture_id int(32) NOT NULL,
    prediction_time varchar(32) NOT NULL,
    team_h_pred int(4) NOT NULL,
    team_a_pred int(4) NOT NULL,
    PRIMARY KEY (user_id, fixture_id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (fixture_id) REFERENCES fixture (id)
);

CREATE TABLE result (
    fixture_id int(32) NOT NULL,
    team_h_score int(4) NOT NULL,
    team_a_score int(4) NOT NULL,
    PRIMARY KEY (fixture_id),
    FOREIGN KEY (fixture_id) REFERENCES fixture (id)
);

CREATE TABLE fixture_score (
    user_id int(32) NOT NULL,
    fixture_id int(32) NOT NULL,
    correct_score BIT NOT NULL,
    correct_outcome BIT NOT NULL,
    correct_gd BIT NOT NULL,
    points int(8) NOT NULL,
    PRIMARY KEY (user_id, fixture_id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (fixture_id) REFERENCES fixture (id)
);

CREATE TABLE gameweek_score (
    user_id int(32) NOT NULL,
    gw int(8) NOT NULL,
    missed_gw BIT NOT NULL,
    total_points int(8) NOT NULL,
    PRIMARY KEY (user_id, gw),
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (gw) REFERENCES gameweek (id)
);

CREATE TABLE leaderboard (
    user_id int(32) NOT NULL,
    total_points int(8) NOT NULL,
    gw int(8) NOT NULL,
    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES user (id)
);
