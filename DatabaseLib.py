import mysql.connector

DATABASE = "predictions_league"
HOST = "localhost"

class DBWriteError( Exception ):
    pass

# TODO: Secure this by verifying that no writes are made here.
def read_query( query ):
    db = mysql.connector.connect(
        host=HOST,
        database=DATABASE
    )
    cursor = db.cursor()

    cursor.execute( query )
    fields = cursor.column_names
    rows = cursor.fetchall()

    result = []
    for row in rows:
        row_dict = dict(zip(fields, row))
        result.append(row_dict)

    return result

def write_insert( table, data, replace=False ):
    db = mysql.connector.connect(
        host=HOST,
        database=DATABASE
    )
    cursor = db.cursor()

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
            # print(f"Inserted Row - {table}: {row}")
        except:
            raise DBWriteError( f"Failed to Insert Row - {table}: {row}" )

    db.commit()
