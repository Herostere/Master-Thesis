import sqlite3
import json


with open('outputs/actions_data_2022_05_30.json', 'r') as json_file:
    loaded_json = json.load(json_file)

print(len(loaded_json))

connection = sqlite3.connect('outputs/actions_data.db')
sqlite_cursor_main = connection.cursor()
number_of_actions = sqlite_cursor_main.execute("SELECT COUNT(owner) FROM actions;").fetchone()[0]
connection.close()
print(number_of_actions)
