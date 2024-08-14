# predictions_league
This is a tailor-made application used to orchestrate a Premier League prediction competition hosted by me. It currently supports predictions from 8 participants on a weekly basis.

## v1
The first version (PL 2023/2024) of this app was hosted on an AWS EC2 instance, and made use of a lambda function to handle prediction updates in a synchronous manner. A SQL database was hosted on AWS RDS. Twilio SMS API was used for communication.

## v2
For the 2024/2025 season, we have decided to go ahead with an email interface for updates, and Google Forms for user input. This allows us to make use of Google Forms' data storage capabilities, meaning that we only need to poll for predictions at the end of a prediction period. We notify participants through the Gmail API. This brings down the required compute to a single python script being run each week. It handles all the required tasks for a given gameweek. A local MySQL instance is being used for storing all the data.

## Post-setup
- `mysql < database/schema.sql` to create the MySQL database and associated tables.
- `mysql < database/data.sql` to load boiler plate data e.g. teams, users, initial leaderboard.
- `python3 main.py` (weekly script run) checks whether there is an upcoming PL gameweek, scores predictions from the previous week, gets upcoming fixtures, creates a Google Form with appropriate questions, sends an email to all participants notifying them of an upcoming gameweek, prompting them to submit their predictions, and providing an overview of the past results and current leaderboard.
