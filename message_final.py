### Get Match Results
### Compute Scores
### DB Insert
### Send Summary Message

import configparser
from event import Event
from premier_league import PL

parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')

class FinalMessage(Event):

    def __init__(self) -> None:

        super().__init__()



if __name__ == "__main__":

    gw = int(sys.argv[1])
    
    Action = FinalMessage()

    