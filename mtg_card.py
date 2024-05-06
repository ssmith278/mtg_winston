import enum
import sqlite3
from sqlite3 import Error

class DBManager():
    def __init__(self) -> None:
        self.connection = None

    def create_connection(self, file_path):
        if self.connected():
            print(f'Attempt to create a connection when a connection is already open.')
            return None

        try:
            self.connection = sqlite3.connect(file_path)
            print(f"Connection to SQLite DB {file_path} successful")
        except Error as e:
            print(f"The error '{e}' occurred")

        return self.connection

    def connected(self):
        try:
            self.connection.cursor()
            return True
        except Exception as e:
            return False

    def close_connection(self):
        self.connection.close()

class CardDatabase():

    def __init__(self, db_name = 'mtg_db.db', card_table_name = 'CARDS') -> None:
        
        self.db = DBManager()
        self.fstrDBName = db_name
        self.fstrCardTableName = card_table_name

        self.db.create_connection(db_name)

    def create_cards_table(self):

        print(f'Opened database {self.fstrDBName} successfully.')

        try:
            self.db.connection.execute(f'''CREATE TABLE {self.fstrCardTableName}
                        (Id TEXT    PRIMARY KEY    NOT NULL,
                        Name    TEXT    NOT NULL,
                        SetName TEXT    NOT NULL,
                        Uri     TEXT    NOT NULL,
                        Cmc     REAL     NOT NULL,
                        TypeLine TEXT   NOT NULL,
                        OracleText  TEXT,
                        Rarity  TEXT    NOT NULL
                        Language TEXT NOT NULL);''')

            print(f'Table {self.fstrCardTableName} created successfully in database {self.fstrDBName}.')

            self.db.connection.commit()            
        except Error as e:
            print(f'The following error occurred when creating cards table: {e}')

    def table_exists(self):
        try:
            self.db.connection.execute(f'SELECT 1 FROM {self.fstrCardTableName} LIMIT 1;')
            return True
        except Error as e:
            print(f'Failed table existence check with error: {e}')

        return False

    def get_card_by_name(self, card_name, language = 'en', exact_match = False):

        if not self.table_exists:
            return None

        #print(f'Getting data for {card_name} in table {self.fstrCardTableName}')
    
        #fields = self.sanitize_field_names('Name', 'fstrSetName', 'Cmc', 'TypeLine')
        fields = self.sanitize_field_names('Name','Uri')
        
        if not exact_match:
            card_name = card_name + '%'

        operator = '=' if exact_match else 'LIKE'

        params = (card_name, language,)
        result = {}
        try:
            cursor = self.db.connection.execute(f'''SELECT {fields}
                        FROM {self.fstrCardTableName} 
                        WHERE Name {operator} ? 
                        AND Language = ?
                        AND TypeLine NOT LIKE 'token%'
                        AND TypeLine NOT LIKE 'emblem%'
                        COLLATE Latin1_general_CI_AI
                        LIMIT 1;''', params)

            result = cursor.fetchone()
            
            if result:
                result = {field : value for field, value in zip(fields.split(','), result)}
                return Card(result), True

            else:
                no_info_card = Card({'Name': card_name})
                return no_info_card, False
        except Error as e:
            print(e)

    
    def sanitize_field_names(self, *fields):
        # TODO: add lines to check that fields contain any invalid characters and/or no-no words
        return ','.join(fields)

    def is_valid_card_list(self, card_list):
        
        failed_cards = []

        for card in card_list:
            _, success = self.get_card_by_name(card, exact_match=True)
            if not success:
                failed_cards.append(card)
                            
        return not failed_cards, failed_cards

class Card():

    class Colors(enum.Enum):
        
        W = 'white'
        U = 'blue'
        B = 'black'
        R = 'red'
        G = 'green'

    def __init__(self, card_dict, card_name='') -> None:
        
        self.card_dict = card_dict
        self.Id = ''
        self.Name = card_name
        self.Uri = ''
        self.Cmc = -1
        self.TypeLine = ''
        self.OracleText = ''
        self.ColorIdentityList = []
        
        if card_dict:
            try:
                self.loadCard()
            except Exception as e:
                print(f'Failed to load card information from dictionary with exception: {e}')

    def loadCard(self):
        self.Id = self.card_dict['Id'] if 'Id' in self.card_dict else ''
        self.Name = self.card_dict['Name'] if 'Name' in self.card_dict else ''
        self.Uri = self.card_dict['Uri'] if 'Uri' in self.card_dict else ''
        self.Cmc = self.card_dict['Cmc'] if 'Cmc' in self.card_dict else -1
        self.TypeLine = self.card_dict['TypeLine'] if 'TypeLine' in self.card_dict else ''
        self.OracleText = self.card_dict['OracleText'] if 'OracleText' in self.card_dict else ''
        self.ColorIdentityList = self.card_dict['ColorIdentityList'] if 'ColorIdentityList' in self.card_dict else []

    def __str__(self):

        result = {}

        for key, value in self.card_dict.items():
            if value:
                result[key] = value 

        return str(result)