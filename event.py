# abstract base class
# all message py files use this

from twilio.rest import Client
import mysql.connector
import configparser

# params.cfg
parser = configparser.ConfigParser()
parser.optionxform = str
parser.read('params.cfg')



from abc import ABC, abstractmethod
 
class Event(ABC):

    def __init__(self):
        
        # Twilio attributes
        self.TWILIO_ACCOUNT_SID = parser.get('twilio','TWILIO_ACCOUNT_SID')
        self.TWILIO_AUTH_TOKEN = parser.get('twilio','TWILIO_AUTH_TOKEN')
        self.SMS_SID = parser.get('twilio','SMS_SID')
        self.CA_FROM_NO = parser.get('twilio','CA_FROM_NO')
        self.UK_FROM_NO = parser.get('twilio','UK_FROM_NO')

        self.client = Client(self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN)

        # MySQL atrtributes
        self.RDS_HOST = parser.get('mysql','host')
        self.RDS_USER = parser.get('mysql','user')
        self.RDS_PASSWORD = parser.get('mysql','password')
        self.DB = parser.get('mysql','database')        
            
    def send_message(self, to_number, message_body):

        local_from_number = self.CA_FROM_NO
        if to_number[:3]=='+44':
            local_from_number = self.UK_FROM_NO
        
        message = self.client.messages.create(
            messaging_service_sid = self.SMS_SID,
            from_ = local_from_number,
            body = message_body,
            to = to_number
        )

        print(message.sid)

    def get_message(self, message_sid):

        return self.client.messages(message_sid).fetch().__dict__


    def read_query(self, query):      
        
        # connect to db
        cnx = mysql.connector.connect(host=self.RDS_HOST, user=self.RDS_USER, password=self.RDS_PASSWORD, database=self.DB)
        cursor = cnx.cursor()

        # execute query
        cursor.execute(query)
        fields = cursor.column_names
        rows = cursor.fetchall()
        
        # close connection
        cursor.close()
        cnx.close()

        # create result dict
        result = []
        for row in rows:
            row_dict = dict(zip(fields, row))
            result.append(row_dict)
        
        return result

    # data: array of dicts with keys corresponding to table fields
    def write_insert(self, table, data, replace=False):

        # connect to db
        cnx = mysql.connector.connect(host=self.RDS_HOST, user=self.RDS_USER, password=self.RDS_PASSWORD, database=self.DB)
        cursor = cnx.cursor()

        for row in data:

            columns = ', '.join(row.keys())
            value_placeholders = ', '.join(['%s'] * len(row))
            values = tuple(row.values())

            SQLAction = "INSERT"
            if replace:
                # primarily used for predictions
                SQLAction = "REPLACE"

            statement = (f"{SQLAction} INTO {table} "
                         f"({columns}) "
                         f"VALUES ({value_placeholders})")

            try:
                cursor.execute(statement, values)
                print(f"Inserted Row - {table}: {row}")
            except:
                print(f"Failed to Insert Row - {table}: {row}")
    
        # commit
        cnx.commit()
        # close connection
        cursor.close()
        cnx.close()
