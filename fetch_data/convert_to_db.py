import json
import os
import sqlite3


def read_json_file(json_file: str):
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    if check_json_content(json_data):
        return json_data
    return {}


def check_json_content(json_data):
    required_keys = ["category", "contributors", "dependents", "forks", "issues", "name", "owner", "repository",
                     "stars", "verified", "versions", "watchers"]
    json_data_keys = json_data[list(json_data.keys())[0]].keys()
    for required_key in required_keys:
        if required_key not in json_data_keys:
            return False
    return True


def convert_json_name(json_file):
    file_without_extension = json_file.split('.json')[0]
    file_database = file_without_extension + ".db"
    return file_database


def create_database(json_data, database_file):
    sqlite_connection = sqlite3.connect(database_file)
    sqlite_cursor = sqlite_connection.cursor()

    sqlite_create_main_table = """
    CREATE TABLE IF NOT EXISTS actions (
        category TEXT,
        forks INTEGER,
        name TEXT,
        owner TEXT,
        repository TEXT,
        stars INTEGER,
        verified INTEGER,
        watchers INTEGER,
        PRIMARY KEY (owner, repository)
    );
    """
    sqlite_create_contributors_table = """
    CREATE TABLE IF NOT EXISTS contributors (
        owner TEXT,
        repository TEXT,
        contributor TEXT,
        PRIMARY KEY (owner, repository, contributor),
        FOREIGN KEY (owner, repository) REFERENCES actions (owner, repository)
    );
    """
    sqlite_create_dependents_table = """
    CREATE TABLE IF NOT EXISTS dependents (
        owner TEXT,
        repository TEXT,
        number INTEGER,
        package_url TEXT,
        PRIMARY KEY (owner, repository),
        FOREIGN KEY (owner, repository) REFERENCES actions (owner, repository)
    );
    """
    sqlite_create_issues_table = """
    CREATE TABLE IF NOT EXISTS issues (
        owner TEXT,
        repository TEXT,
        closed INTEGER,
        open INTEGER,
        PRIMARY KEY (owner, repository),
        FOREIGN KEY (owner, repository) REFERENCES actions (owner, repository)
    );
    """
    sqlite_create_versions_table = """
    CREATE TABLE IF NOT EXISTS versions (
        owner TEXT,
        repository TEXT,
        date TEXT,
        version TEXT,
        PRIMARY KEY (owner, repository, date, version),
        FOREIGN KEY (owner, repository) REFERENCES actions (owner, repository)
    );
    """

    sqlite_queries = [sqlite_create_main_table, sqlite_create_contributors_table, sqlite_create_dependents_table,
                      sqlite_create_issues_table, sqlite_create_versions_table]
    for query in sqlite_queries:
        sqlite_cursor.execute(query)

    sqlite_connection.commit()

    for action in json_data:
        owner = json_data[action]["owner"]
        repository = json_data[action]["repository"]
        insert_actions(json_data[action], sqlite_cursor, owner, repository)
        insert_contributors(json_data[action], sqlite_cursor, owner, repository)
        insert_dependents(json_data[action], sqlite_cursor, owner, repository)
        insert_issues(json_data[action], sqlite_cursor, owner, repository)
        insert_versions(json_data[action], sqlite_cursor, owner, repository)
        sqlite_connection.commit()

    sqlite_connection.close()


def insert_actions(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert basic information in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    category = action_data["category"]
    forks = action_data["forks"]
    name = action_data["name"]
    stars = action_data["stars"]
    verified = 1 if action_data["verified"] else 0
    watchers = action_data["watchers"]
    insert_main = """
    INSERT INTO actions (category, forks, name, owner, repository, stars, verified, watchers)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        cursor.execute(insert_main, (category, forks, name, owner, repository, stars, verified, watchers))
    except sqlite3.IntegrityError:
        pass


def insert_contributors(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert the contributors data in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    contributors = action_data["contributors"]
    for contributor in contributors:
        insert_contributor = """
        INSERT INTO contributors (owner, repository, contributor)
        VALUES (?, ?, ?);
        """
        try:
            cursor.execute(insert_contributor, (owner, repository, contributor))
        except sqlite3.IntegrityError:
            pass


def insert_dependents(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert dependents data in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    dependents = action_data["dependents"]
    number = dependents["number"]
    package_url = dependents["package_url"]
    insert_dependent = """
    INSERT INTO dependents (owner, repository, number, package_url)
    VALUES (?, ?, ?, ?);
    """
    try:
        cursor.execute(insert_dependent, (owner, repository, number, package_url))
    except sqlite3.IntegrityError:
        pass


def insert_issues(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert issues data in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    issues = action_data["issues"]
    closed_issues = issues["closed"]
    open_issues = issues["open"]
    insert_issue = """
    INSERT INTO issues (owner, repository, closed, open)
    VALUES (?, ?, ?, ?);
    """
    try:
        cursor.execute(insert_issue, (owner, repository, closed_issues, open_issues))
    except sqlite3.IntegrityError:
        pass


def insert_versions(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert versions data in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    versions = action_data["versions"]
    for version in versions:
        date = version[0]
        tag = version[1]
        insert_version = """
        INSERT INTO versions (owner, repository, date, version)
        VALUES (?, ?, ?, ?);
        """
        try:
            cursor.execute(insert_version, (owner, repository, date, tag))
        except sqlite3.IntegrityError:
            pass


if __name__ == "__main__":
    json_files_main = [f"outputs/{file}" for file in os.listdir("outputs/") if "json" in file]
    for json_file_main in json_files_main:
        json_data_main = read_json_file(json_file_main)
        if json_data_main:
            database_file_main = convert_json_name(json_file_main)
            create_database(json_data_main, database_file_main)
