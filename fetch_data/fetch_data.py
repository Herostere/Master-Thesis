"""
This script identify the actions with a valid marketplace page.

You will need to use Python3.10.
"""
import json.decoder

from bs4 import BeautifulSoup
from datetime import datetime
from html import unescape
from lxml import html, etree
from ratelimit import limits, sleep_and_retry

import fetch_data_config as config
import logging
import numpy
import os
import re
import requests
import requests.adapters
import sqlite3
import threading
import time


GITHUB_TOKENS = config.tokens
CURRENT_TOKEN = GITHUB_TOKENS[0]
LIMIT = config.limit_requests
SESSION = requests.Session()
SESSION.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")
T_R = 0
ACTION_ACCEPTED = True
CURRENT_DATE = datetime.strftime(datetime.now(), "%Y_%m_%d")
NUMBER_OF_ACCEPTED_ACTIONS = 0


def get_categories() -> None:
    """
    Save the list of GitHub Actions categories as a numpy array.
    """
    logging.info("Fetching the categories")
    save_categories = []
    url = "https://github.com/marketplace?type=actions"

    request = get_request("get_categories", url)

    if not request:
        logging.error("Not supposed to happen...")
        exit()

    root = beautiful_html(request.text)

    result = root.xpath('//*[@id="js-pjax-container"]/div[2]/div[1]/nav/ul[2]/li/a/text()')

    pattern = re.compile(r'[^a-zA-Z ]')

    for li in result:
        category = re.sub(re.compile(r" {2,}"), '', re.sub(pattern, '', li).lower()).replace(' ', '-')
        save_categories.append(category)

    logging.info(f"Categories: \n{save_categories}")

    save_categories = numpy.array(save_categories)

    if config.override_save_categories["run"]:
        save_categories = config.override_save_categories["categories"]
        save_categories = numpy.array(save_categories)

    numpy.save("categories.npy", save_categories)


@sleep_and_retry
@limits(calls=LIMIT, period=60.0)
def get_request(function: str, url: str) -> requests.Response | None:
    """
    Send a request to a webpage and returns the response.

    :param function: The name of the calling function.
    :param url: The url to connect to.
    :return: The response. If error 404, returns None.
    """
    global T_R
    global SESSION

    sleep_time = 30

    while True:
        try:
            request = SESSION.get(url)
            T_R += 1

            if T_R % config.limit_requests == 0:
                logging.info(f"request {T_R}")

            counter = 5

            while counter > 0 and request.status_code != 200:
                if request.status_code == 429:
                    logging.info(">" + str(T_R))
                    logging.info(
                        f"{function} - sleeping " + str(int(request.headers["Retry-After"]) + 0.3) + " seconds")
                    time.sleep(int(request.headers["Retry-After"]) + 0.3)
                    logging.info(f"{function} - sleeping finished")

                    time.sleep(3)
                    request = SESSION.get(url)
                    T_R += 1

                    if T_R % config.limit_requests == 0:
                        logging.info(f"request {T_R}")

                elif request.status_code == 404 and counter == 1:
                    return None

                else:
                    counter -= 1
            break

        except (requests.ConnectionError, requests.exceptions.ReadTimeout, KeyError):
            SESSION.close()
            SESSION = requests.Session()
            SESSION.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")
            try:
                threads = max(10, number_of_threads)
            except NameError:
                threads = 10
            adapter = requests.adapters.HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
            SESSION.mount("https://", adapter)
            SESSION.mount("http://", adapter)
            time.sleep(sleep_time)

    return request


def beautiful_html(request_text: str) -> html.document_fromstring:
    """
    Parse the HTML response and prettify it.

    :param request_text: The HTML response as text.
    :return: A prettified version of the HTML. It is a html.document_fromstring object.
    """
    soup = BeautifulSoup(request_text, 'html.parser')
    pretty_soup = soup.prettify()
    root = html.fromstring(pretty_soup)

    return root


def fetch_data_multithread() -> None:
    """
    Retrieve information about each Action.
    """
    global number_of_threads
    categories = numpy.load("categories.npy")

    sqlite_connection = sqlite3.connect(file_name_main)
    sqlite_cursor = sqlite_connection.cursor()

    sqlite_create_main_table = """
    CREATE TABLE IF NOT EXISTS actions (
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
    sqlite_create_categories_table = """
    CREATE TABLE IF NOT EXISTS categories (
        owner TEXT,
        repository TEXT,
        category TEXT,
        PRIMARY KEY (owner, repository, category),
        FOREIGN KEY (owner, repository) REFERENCES actions (owner, repository)
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
        state TEXT,
        created TEXT,
        closed TEXT,
        PRIMARY KEY (owner, repository, state, created, closed),
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

    sqlite_queries = [sqlite_create_main_table, sqlite_create_categories_table, sqlite_create_contributors_table,
                      sqlite_create_dependents_table, sqlite_create_issues_table, sqlite_create_versions_table]
    for query in sqlite_queries:
        sqlite_cursor.execute(query)

    sqlite_connection.commit()

    logging.info("Fetching the data")
    for category in categories:
        global ACTION_ACCEPTED
        global NUMBER_OF_ACCEPTED_ACTIONS
        ACTION_ACCEPTED = True
        NUMBER_OF_ACCEPTED_ACTIONS = 0
        logging.info(f"***** {category} *****")

        max_page_number = get_max_page(category)

        if max_page_number == 0:
            ACTION_ACCEPTED = False

        number_of_threads = get_number_of_threads(max_page_number)

        adapter = requests.adapters.HTTPAdapter(pool_connections=number_of_threads, pool_maxsize=number_of_threads)
        SESSION.mount("https://", adapter)
        SESSION.mount("http://", adapter)

        refused_counter = 10

        while ACTION_ACCEPTED and refused_counter > 0:
            print("\n" + "*" * 10 + f" loop {category} / {refused_counter}")
            ACTION_ACCEPTED = False
            threads = []

            already_fetched = sqlite_cursor.execute("SELECT owner, repository, category FROM categories;").fetchall()
            save_data = {}

            if number_of_threads > 0:
                for i in range(0, number_of_threads):
                    list_of_pages = [x for x in range(1, max_page_number + 1) if x % number_of_threads == i]
                    list_of_pages.sort()
                    threads.append(threading.Thread(target=thread_data,
                                                    args=(list_of_pages, category, save_data, already_fetched),
                                                    name=f"thread_{i}"))

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

            for action in save_data:
                owner = save_data[action]["owner"]
                repository = save_data[action]["repository"]
                insert_actions(save_data[action], sqlite_cursor, owner, repository)
                insert_categories(save_data[action], sqlite_cursor, owner, repository)
                insert_contributors(save_data[action], sqlite_cursor, owner, repository)
                insert_dependents(save_data[action], sqlite_cursor, owner, repository)
                insert_issues(save_data[action], sqlite_cursor, owner, repository)
                insert_versions(save_data[action], sqlite_cursor, owner, repository)
                sqlite_connection.commit()

            if not ACTION_ACCEPTED:
                ACTION_ACCEPTED = True
                refused_counter -= 1
            else:
                refused_counter = 10

    sqlite_connection.close()


def insert_actions(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert basic information in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    if "forks" in action_data.keys():
        forks = action_data["forks"]
    if "name" in action_data.keys():
        name = action_data["name"]
    if "stars" in action_data.keys():
        stars = ["stars"]
    if "verified" in action_data.keys():
        verified = 0 if action_data["verified"] else 1
    if "watchers" in action_data.keys():
        watchers = action_data["watchers"]
    insert_main = """
    INSERT INTO actions (forks, name, owner, repository, stars, verified, watchers)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    try:
        cursor.execute(insert_main, (forks, name, owner, repository, stars, verified, watchers))
    except (sqlite3.IntegrityError, UnboundLocalError):
        pass


def insert_categories(action_data: dict, cursor: sqlite3.Cursor, owner: str, repository: str) -> None:
    """
    Insert categories information in the database.

    :param action_data: The data to insert.
    :param cursor: The cursor used to add the data.
    :param owner: The name of the owner.
    :param repository: The name of the repository.
    """
    category = action_data["category"]
    insert_category = """
    INSERT INTO categories (owner, repository, category)
    VALUES (?, ?, ?);
    """
    try:
        cursor.execute(insert_category, (owner, repository, category))
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
    if "contributors" in action_data.keys():
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
    if "dependents" in action_data.keys():
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
    if "issues" in action_data.keys():
        issues = action_data["issues"]
        if len(issues) == 0:
            state = None
            created = None
            closed = None
            insert_issue = """
            INSERT INTO issues (owner, repository, state, created, closed)
            VALUES (?, ?, ?, ?, ?);
            """
            try:
                cursor.execute(insert_issue, (owner, repository, state, created, closed))
            except sqlite3.IntegrityError:
                pass
        for issue in issues:
            state = issue[0]
            created = issue[1]
            closed = issue[2]
            insert_issue = """
            INSERT INTO issues (owner, repository, state, created, closed)
            VALUES (?, ?, ?, ?, ?);
            """
            try:
                cursor.execute(insert_issue, (owner, repository, state, created, closed))
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
    if "versions" in action_data.keys():
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


def get_max_page(category: str) -> int:
    """
    Get the number of the last page. It is useful to know it for multithreading.

    :param category: The category we are interested of knowing the number of pages.
    :return: The number of the last page. Returns 0 if there is no Actions in this category.
    """
    url = f"https://github.com/marketplace?category={category}&page=1&type=actions"

    request = get_request("get_max_page", url)

    page_xpath_0 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/a[not(@class="next_page")]'
    page_xpath_1 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/em'
    page_xpath = f'{page_xpath_0} | {page_xpath_1}'

    root = beautiful_html(request.text)
    numbers = root.xpath(page_xpath)
    last_index = len(numbers) - 1

    if last_index > 0:
        max_page = re.sub(re.compile(r"\s{2,}"), '', numbers[last_index].text)
        logging.info("Number of pages: " + str(max_page))
        return int(max_page)
    else:
        logging.info("Number of pages: " + str(0))
        return 0


def get_number_of_threads(max_page_number: int) -> int:
    """
    Fetching the number of threads to use.

    :param max_page_number: The number of pages on the GitHub marketplace.
    :return: The number of threads to use.
    """
    num_of_threads = config.fetch_data["max_threads"]
    try:
        num_of_threads = int(num_of_threads)
        # the point here is not to allow more threads then the number of pages
        if num_of_threads > max_page_number:
            num_of_threads = max_page_number
        if num_of_threads < 1:
            num_of_threads = 0
    except ValueError:
        logging.error("Bad number of threads in configuration file.\nBad value is " + num_of_threads)
        num_of_threads = 19  # this value has been chosen because "trust me".
    logging.info("Number of threads: " + str(num_of_threads))

    return num_of_threads


def thread_data(pages: list, category: str, save_data: dict, already_fetched: list) -> None:
    """
    For each Action on a category:
        - Check if it has a valid MP page.
        - If so, check if it has a valid link to a github page.
        - If so, get some data about it.

    :param pages: The list of pages on which fetch the actions names.
    :param category: The category of GitHub Actions.
    :param save_data: The data to save in the database.
    :param already_fetched: The already fetched data.
    """
    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    for page in pages:
        url = f"https://github.com/marketplace?category={category}&page={page}&type=actions"

        request = get_request("fetch_names", url)
        root = beautiful_html(request.text)

        actions_names_ugly = actions_names_pattern_compiled.findall(request.text)
        actions_urls = root.xpath("//div[@class='d-md-flex flex-wrap mb-4']/a/@href")

        for j in range(0, len(actions_names_ugly)):
            action_name = format_action_name(actions_names_ugly[j])
            mp_page, action_url = test_mp_page(actions_urls[j])
            if mp_page:
                owner = get_owner(action_url)
                repository_name = get_repo_name(action_url)
                if (owner, repository_name, category) not in already_fetched:
                    pretty_name = f'{owner}/{repository_name}'
                    data = test_link(action_url)
                    if data:
                        global ACTION_ACCEPTED
                        global NUMBER_OF_ACCEPTED_ACTIONS
                        NUMBER_OF_ACCEPTED_ACTIONS += 1
                        print(f"\r{NUMBER_OF_ACCEPTED_ACTIONS} actions accepted.", end='')
                        ACTION_ACCEPTED = True
                        save_data[pretty_name] = {}
                        save_data[pretty_name]['category'] = category
                        verified = get_verified(mp_page)
                        save_data[pretty_name]['verified'] = verified
                        save_data[pretty_name]['owner'] = owner
                        save_data[pretty_name]['repository'] = repository_name
                        save_data[pretty_name]['name'] = format_action_name(actions_names_ugly[j])

                        if config.fetch_categories["versions"]:
                            versions = get_api('versions', owner, repository_name)
                            save_data[pretty_name]['versions'] = versions

                        if config.fetch_categories["dependents"]:
                            dependents = get_dependents(owner, repository_name)
                            save_data[pretty_name]['dependents'] = {}
                            save_data[pretty_name]['dependents']['number'] = dependents[0]
                            save_data[pretty_name]['dependents']['package_url'] = dependents[1]

                        if config.fetch_categories["contributors"]:
                            contributors = get_api('contributors', owner, repository_name)
                            contributors.sort()
                            save_data[pretty_name]['contributors'] = contributors

                        if config.fetch_categories["stars"]:
                            stars = get_api("stars", owner, repository_name)
                            save_data[pretty_name]["stars"] = stars

                        if config.fetch_categories["watchers"]:
                            watchers = get_api("watchers", owner, repository_name)
                            save_data[pretty_name]["watchers"] = watchers

                        if config.fetch_categories["forks"]:
                            forks = get_api("forks", owner, repository_name)
                            save_data[pretty_name]["forks"] = forks

                        if config.fetch_categories["issues"]:
                            issues = get_api("issues", owner, repository_name)
                            save_data[pretty_name]["issues"] = issues
                    else:
                        print(f"\r{action_name} refused 2.", end="\n")
            else:
                print(f"\r{action_name} refused 1.", end="\n")


def format_action_name(ugly_name: str) -> str:
    """
    Format the name of the Action to fit with the format used by GitHub in the URLs.

    :param ugly_name: The name that has to be formatted.
    :return: The prettified name.
    """
    ugly_name = ugly_name.split('<h3 class="h4">')[1].split('</h3>')[0].lower()
    ugly_name = unescape(ugly_name)  # convert html code to utf-8 ex: &quot becomes "
    ugly_name = ugly_name.replace(" - ", "-").replace(" ", "-")
    ugly_name = re.sub("[^0-9a-zA-Z_-]", "-", ugly_name)

    # Removes '-' at the beginning and the end of a name.
    while re.search("^-.*$", ugly_name):
        ugly_name = ugly_name[1:]
    while re.search("^.*-$", ugly_name):
        ugly_name = ugly_name[:-1]

    ugly_name = re.sub("-{2,}", "-", ugly_name)

    return ugly_name


def test_mp_page(url: str) -> tuple[requests.Response, str] | tuple[None, None]:
    """
    Test if the marketplace page of an Action is accessible and returns the URL for the data if so.

    :param url: The URL of the Action to check.
    :return: The response and the URL of the GitHub page if the marketplace page is accessible.
             Otherwise returns None, None.
    """
    url = f"https://github.com{url}"
    request = get_request("test_name", url)

    if request:
        root = beautiful_html(request.text)
        url = root.xpath('//h5[text()="\n          Links\n         "]/following-sibling::a[1]/@href')
        if url:
            return request, url[0]
        return None, None
    return None, None


def test_link(url: str) -> str | None:
    """
    Test if a link is valid and return it's content.

    :param url: The URL to check.
    :return: The content if the URL is accessible. Otherwise None.
    """
    request = get_request("test_link", url)

    if request:
        return request.text
    return None


def get_verified(mp_page: requests.Response) -> bool:
    """
    Determine if it is a GitHub action developed by a verified user.

    :param mp_page: The Response used to determine if it is an Action developed by a verified user or not.
    :return: True if it is a verified Action and False otherwise.
    """
    xpath = '//*[text()[contains(., "Verified creator")]]'
    root = beautiful_html(mp_page.text)

    verified = root.xpath(xpath)

    return True if verified else False


def get_owner(url: str) -> str:
    """
    Get the owner of a repo.

    :param url: The URL on which the owner will be retrieved.
    :return: The owner of the repo.
    """
    return url.split("https://github.com/")[1].split("/")[0]


def get_repo_name(url: str) -> str:
    """
    Get the name of the repo.

    :param url: The URL on which the name of the repo will be retrieved.
    :return: The name of the repo.
    """
    return url.split('https://github.com/')[1].split('/')[1]


def get_api(key: str, owner: str, repo_name: str) -> int | dict | list:
    """
    Contact the API to fetch information.

    :param key: The kind of data to retrieve.
    :param owner: The owner of the repository.
    :param repo_name: The name of the repository.
    :return: A tuple with an integer, a list or a dictionary, depending of the nature of the needed information and
             the index for the next API call.
    """
    if key != "contributors":
        queries = {"versions": "releases(first: 100) { totalCount edges { cursor node { tag { name } publishedAt } } }",
                   "stars": "stargazerCount",
                   "watchers": "watchers { totalCount }",
                   "forks": "forks { totalCount }",
                   "issues": "issues(first: 100) { totalCount edges { cursor node { state createdAt closedAt } } }",
                   }

        query = {'query': f"""
        {{
          repositoryOwner(login: "{owner}") {{
            login
            repository(name: "{repo_name}") {{
              name
              {queries[key]}
            }}
          }}
        }}
        """}

        api_answer = request_to_api(query)

        needed_data = extract(api_answer, key)

        return needed_data
    else:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors?per_page=100&page=1"
        final = []
        api_answer = request_to_api(None, url)
        while 'next' in api_answer.links.keys():
            temp = extract(api_answer, "contributors")
            for element in temp:
                if element not in final:
                    final.append(element)
            api_answer = request_to_api(None, api_answer.links['next']['url'])
        temp = extract(api_answer, "contributors")
        for element in temp:
            if element not in final:
                final.append(element)
        return final


def request_to_api(query: dict | None, url: str = None) -> requests.Response | None:
    """
    Make a request to the GitHub's GraphQL API.

    :param query: The query to get the information.
    :param url: The url to use for REST API issues.
    :return: The API response or None if error in response.
    """
    tries = 10
    api_call = None
    if query:
        while tries > 0:
            url = "https://api.github.com/graphql"

            try:
                while not get_remaining_api_calls():
                    time.sleep(60)
                headers = {
                    'Authorization': f'token {CURRENT_TOKEN}',
                }
                api_call = requests.post(url, json=query, headers=headers)
                api_call_json = api_call.json()
                if "errors" in api_call_json:
                    tries -= 1
                    api_call = None
                else:
                    return api_call

            except requests.exceptions.ConnectionError:
                time.sleep(60)
                return request_to_api(query)
            except requests.exceptions.ChunkedEncodingError:
                return None
            except json.decoder.JSONDecodeError:
                return None

    else:
        try:
            while not get_remaining_api_calls(True):
                time.sleep(60)
            headers = {
                'Authorization': f'token {CURRENT_TOKEN}',
                'accept': 'application/vnd.github.v3+json',
            }
            api_call = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError:
            time.sleep(60)
            return request_to_api(None, url)

    return api_call


def extract(api_answer: requests.Response, key: str) -> int | dict | list:
    """
    Extract the information from the API.

    :param api_answer: The answer from the API.
    :param key: The information we need to extract.
    :return: The extracted information in a list or dictionary and the index for the API.
    """
    if key != "contributors":
        data = api_answer.json()["data"]["repositoryOwner"]["repository"]

        if key == "versions":
            final_releases = []
            gathered_releases = extract_all(api_answer, key)
            for release in gathered_releases:
                try:
                    tag = release["node"]["tag"]["name"]
                except TypeError:
                    tag = None
                date = datetime.strptime(release["node"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
                date = date.strftime("%Y-%m-%d %H:%M:%S")
                final_releases.append((date, tag))
            return final_releases

        elif key == "stars":
            stars = data["stargazerCount"]
            return stars

        elif key == "watchers":
            watchers = data["watchers"]["totalCount"]
            return watchers

        elif key == "forks":
            forks = data["forks"]["totalCount"]
            return forks

        elif key == "issues":
            final_issues = []
            gathered_issues = extract_all(api_answer, key)
            for issue in gathered_issues:
                try:
                    state = issue["node"]["state"]
                    created_at = issue["node"]["createdAt"]
                    closed_at = issue["node"]["closedAt"]
                    final_issues.append((state, created_at, closed_at))
                except KeyError:
                    continue
            return final_issues

    else:
        extracted = []
        for needed in api_answer.json():
            extracted.append(needed["login"])
        return extracted


def extract_all(api_answer: requests.Response, key: str) -> list:
    """
    Extract the data when there is possibly multiple pages of answer.

    :param api_answer: The answer of the API call.
    :param key: The key for the wanted data.
    """
    version_query = """
    releases(first: 100, after:{after}) {{ totalCount edges {{ cursor node {{ tag {{ name }} publishedAt }} }} }}
    """
    queries = {
        "versions": version_query,
        "issues": "issues(first: 100, after:{after}) {{ totalCount edges {{ cursor node {{ state }} }} }}",
    }
    to_extract = {"versions": "releases", "issues": "issues"}

    owner = api_answer.json()["data"]["repositoryOwner"]["login"]
    repository_name = api_answer.json()["data"]["repositoryOwner"]["repository"]["name"]
    data = api_answer.json()["data"]["repositoryOwner"]["repository"]

    extracted_data = data[to_extract[key]]
    total_count = extracted_data["totalCount"]
    gathered_data = extracted_data["edges"]
    total_gathered = len(gathered_data)
    while total_gathered < total_count:
        last_gathered_cursor = f'"{extracted_data["edges"][-1]["cursor"]}"'
        query = {'query': f"""
        {{
          repositoryOwner(login: "{owner}") {{
            login
            repository(name: "{repository_name}") {{
              name
              {queries[key].format(after=last_gathered_cursor)}
            }}
          }}
        }}
        """}
        new_api_answer = request_to_api(query)
        gathered_data += new_api_answer.json()["data"]["repositoryOwner"]["repository"][to_extract[key]]["edges"]

        total_gathered = len(gathered_data)

    return gathered_data


def get_remaining_api_calls(rest: bool = False) -> bool:
    """
    Tells if API calls can be made or not.
    Always switch to the first token with remaining calls.

    :param rest: Indicate if we check for the REST of GraphQL API.
    :return: True if there can be API requests. Otherwise, False.
    """
    global CURRENT_TOKEN

    if not rest:
        url = "https://api.github.com/graphql"
        for token in GITHUB_TOKENS:
            while True:
                try:
                    headers = {
                        'Authorization': f'token {token}',
                    }
                    query = {"query": "{ rateLimit { remaining resetAt } }"}
                    api_call = requests.post(url, json=query, headers=headers)
                    rate_limit = api_call.json()["data"]["rateLimit"]

                    if rate_limit["remaining"] > 0:
                        CURRENT_TOKEN = token
                        return True

                    break
                except (TypeError, json.decoder.JSONDecodeError, KeyError):
                    time.sleep(1)
    else:
        for token in GITHUB_TOKENS:
            headers = {
                'Authorization': f'token {token}',
                'accept': 'application/vnd.github.v3+json',
            }
            api_call = requests.get("http://api.github.com/rate_limit", headers=headers)
            if int(api_call.headers['X-RateLimit-Remaining']) > 0:
                CURRENT_TOKEN = token
                return True
    return False


def get_dependents(owner: str, repo_name: str) -> tuple[int, str]:
    """
    Get the number of dependents and the corresponding package url for a repository.

    :param owner: The owner of the repository.
    :param repo_name: The name of the repository.
    :return: The number of dependents and the url to get the dependents sample.
    """
    url = f"https://github.com/{owner}/{repo_name}/network/dependents"
    xpath_is_packages = '//*[@id="dependents"]/details/summary/i/text()'
    xpath_packages = '//*[@id="dependents"]/details/details-menu/div[2]/a/@href'

    root = get_dependents_html(url)

    ugly_packages = root.xpath(xpath_is_packages)
    packages = []
    if ugly_packages:
        packages = root.xpath(xpath_packages)
        for i, urls in enumerate(packages):
            packages[i] = "https://github.com" + urls

    max_url = url if "https://github.com" in url else "https://github.com" + url
    max_dependents = get_dependents_number(root)
    if packages:
        for urls in packages:
            root_package = get_dependents_html(urls)
            dependents = get_dependents_number(root_package)
            if dependents > max_dependents:
                max_url = urls
                max_dependents = dependents

    return max_dependents, max_url


def get_dependents_html(url: str) -> html.document_fromstring:
    """
    Get the html for a dependents page.

    :param url: The url for the dependents.
    :return: The response as an html.document_fromstring object.
    """
    root = None

    while True:
        try:
            request = get_request("get_dependents", url)
            root = beautiful_html(request.text)
            break
        except etree.ParserError:
            continue

    return root


def get_dependents_number(root: html.document_fromstring) -> int:
    """
    Get the number of dependents on a page.

    :param root: The html where the dependents are located.
    :return: The number of dependents.
    """
    xpath_dependents_number = '//*[@id="dependents"]/div[3]/div[1]/div/div/a[1]/text()'

    try:
        ugly_dependents = root.xpath(xpath_dependents_number)[1]
    except IndexError:
        return 0

    dependents_temp = re.findall(re.compile(r'\d+'), ugly_dependents)
    if dependents_temp:
        dependents = int(''.join(dependents_temp))
        return dependents
    return 0


if __name__ == "__main__":
    start_time = time.time()

    """
    Logging config.
    """
    log_file_name = "fetch_data.log"
    logging.basicConfig(filename=log_file_name, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')

    """
    Starting fetching.
    """
    logging.info("Starting program")

    run = config.run
    if run:
        """
        Fetch the categories.
        """
        file_name_main = f"outputs/actions_data_{CURRENT_DATE}.db"

        number_of_threads = 0
        # SESSION = requests.Session()
        # SESSION.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")

        run_categories = config.get_categories['run']
        if run_categories:
            get_categories()

        """
        Main steps of the code. Retrieves the data.
        """
        run_fetch_data = config.fetch_data['run']
        if run_fetch_data:
            fetch_data_multithread()

            sqlite_connection_main = sqlite3.connect(file_name_main)
            sqlite_cursor_main = sqlite_connection_main.cursor()
            number_of_actions = sqlite_cursor_main.execute("SELECT COUNT(owner) FROM actions;").fetchone()[0]
            sqlite_connection_main.close()

            logging.info(f"Number of fetched actions: {number_of_actions}")
        else:
            logging.info(f"Number of fetched actions: N/A")

        SESSION.close()

    logging.info(f"--- {time.time() - start_time} seconds ---")
