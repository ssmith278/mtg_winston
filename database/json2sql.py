import json
import sqlite3 as sql
from sqlite3 import Error
import os
import db_mgr as dbm
from tqdm import tqdm

dbmgr = dbm.DBManager()
card_db = []

file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'oracle-cards-20240416210234.json')

def getValue(card_json, key):
    if key in card_json:
        value = card_json[key]
        return value

    return None

def quote(string):
    return f'\'{string}\''

current_count = 0

with open(file_path, 'r', encoding='utf8') as infile:

    for line in tqdm(infile, total=sum(1 for _ in open(file_path, 'r', encoding='utf8'))):
        line = line.strip()
        line = line.removesuffix(',')
        card = json.loads(line)
        card_db.append({
            'Id': getValue(card,'id'), 
            'Name': getValue(card,'name'), 
            'Uri': getValue(card,'scryfall_uri'), 
            'ImageUris': getValue(card,'image_uris'), 
            'ManaCost': getValue(card,'mana_cost'), 
            'Cmc': getValue(card,'cmc'),
            'TypeLine': getValue(card,'type_line'),
            'OracleText': getValue(card,'oracle_text'),
            'Power': getValue(card,'power'),
            'Toughness': getValue(card,'toughness'),
            'Colors': getValue(card,'colors'),
            'ColorIdentityList': getValue(card,'color_identity'),
            'fstrSet': getValue(card,'set'),
            'SetName': getValue(card,'set_name'),
            'Rarity': getValue(card,'rarity'),
            'Language': getValue(card, 'lang')})

        current_count += 1

db_name = 'card_database.db'
conn = dbmgr.create_connection(file_path=db_name)

print(f'Opened database {db_name} successfully.')

try:
    conn.execute('''CREATE TABLE CARDS
                (Id TEXT    PRIMARY KEY    NOT NULL,
                Name    TEXT    NOT NULL,
                SetName TEXT    NOT NULL,
                Uri     TEXT    NOT NULL,
                Cmc     REAL     NOT NULL,
                TypeLine TEXT   NOT NULL,
                OracleText  TEXT,
                Rarity  TEXT    NOT NULL,
                Language TEXT NOT NULL);''')
except Error as e:
    print(f'The following error occurred when creating cards table: {e}')
    
    try:
        conn.execute('DELETE FROM CARDS')
    except Error as e:
        print(f'Failed to delete from cards with error: {e}')
        exit

for entry in card_db:
    conn.execute(f'INSERT INTO CARDS (Id, Name, SetName, Uri, Cmc, TypeLine, OracleText, Rarity, Language) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', 
        (entry["Id"], 
        entry["Name"], 
        entry["SetName"] or '', 
        entry["Uri"] or '', 
        float(entry["Cmc"] or 0), 
        entry["TypeLine"] or '',
        entry["OracleText"] or '', 
        entry["Rarity"] or '',
        entry["Language"] or ''))

conn.commit()
conn.close()