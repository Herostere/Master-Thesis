"""
This script identify the actions with a valid marketplace page.

You will need to use Python3.10.
"""
from bs4 import BeautifulSoup
from html import unescape
from lxml import html
from ratelimit import limits, sleep_and_retry

import fetch_data_config as config
import json
import logging
import numpy
import os
import re
import requests
import requests.adapters
import threading
import time


try:
    with open("actions_data.json", 'r') as f:
        DATA = json.load(f)
except FileNotFoundError:
    DATA = json.loads('{}')

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LIMIT = config.limit_requests
T_R = 0


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

    """
    TO DELETE
    """
    save_categories = ["monitoring"]
    save_categories = numpy.array(save_categories)
    """
    -----
    """

    numpy.save("categories.npy", save_categories)


@sleep_and_retry
@limits(calls=LIMIT, period=60.0)
def get_request(function: str, url: str) -> requests.Response | None:
    """
    Get a webpage.

    :param function: The name of the calling function.
    :param url: The url to connect to.
    :return: The response. If error 404, returns None.
    """
    global T_R
    global session

    while True:
        try:
            request = session.get(url)
            break
        except requests.ConnectionError:
            session.close()
            session = requests.Session()
            session.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")
            return get_request(function, url)
    T_R += 1

    logging.info(f"request {T_R}")

    if request.status_code != 200:
        if request.status_code == 429:
            logging.info(">" + str(T_R))
            logging.info(f"{function} - sleeping " + str(int(request.headers["Retry-After"]) + 0.3) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 0.3)
            logging.info(f"{function} - sleeping finished")
            return get_request(function, url)
        if request.status_code == 404:
            return None
        T_R += 1

    return request


def beautiful_html(request_text: str) -> html.document_fromstring:
    """
    Parse the html response and prettify it.

    :param request_text: The html response as text.
    :return: A prettified version of the html. It is a html.document_fromstring object.
    """
    soup = BeautifulSoup(request_text, 'html.parser')
    pretty_soup = soup.prettify()
    root = html.fromstring(pretty_soup)

    return root


def fetch_data_multithread() -> None:
    """
    Retrieve information about each Action.
    """
    categories = numpy.load("categories.npy")

    logging.info("Fetching the data")

    for category in categories:
        logging.info(f"***** {category} *****")

        max_page_number = get_max_page(category)

        number_of_threads = get_number_of_threads(max_page_number)

        adapter = requests.adapters.HTTPAdapter(pool_connections=number_of_threads, pool_maxsize=number_of_threads)
        session.mount("https://", adapter)

        threads = []

        for i in range(0, number_of_threads):
            list_of_pages = [x for x in range(1, max_page_number + 1) if x % number_of_threads == i]
            threads.append(threading.Thread(target=thread_data, args=(list_of_pages, category,), name=f"thread_{i}"))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


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
        elif num_of_threads < 1:
            num_of_threads = 1
    except ValueError:
        logging.error("Bad number of threads in configuration file.\nBad value is " + num_of_threads)
        num_of_threads = 19  # this value has been chosen because "trust me".
    logging.info("Number of threads: " + str(num_of_threads))

    return num_of_threads


def thread_data(pages: list, category: str) -> None:
    """
    For each Action on a category:
        - Check if it has a valid MP page.
        - If so, check if it has a valid link to a github page.
        - If so, get some data about it.

    :param pages: The list of pages on which fetch the actions names.
    :param category: The category of GitHub Actions.
    """
    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    for page in pages:
        url = f"https://github.com/marketplace?category={category}&page={page}&query=&type=actions"

        request = get_request("fetch_names", url)

        actions_names_ugly = actions_names_pattern_compiled.findall(request.text)

        # Below is used to format the name as in the marketplace urls.
        for j in range(0, len(actions_names_ugly)):
            pretty_name = format_action_name(actions_names_ugly[j])
            already_fetched = DATA.keys()
            if pretty_name not in already_fetched:
                mp_page, url = test_mp_page(pretty_name)
                if mp_page:
                    data = test_link(url)
                    if data:
                        # official = get_official(url)
                        owner = get_owner(url)
                        repo_name = get_repo_name(url)
                        # versions = get_versions(owner, repo_name)
                        # stars = get_api('stars', owner, repo_name)
                        dependents = get_dependents(owner, repo_name)

                        DATA[pretty_name] = {}
                        DATA[pretty_name]['category'] = category
                        # DATA[pretty_name]['official'] = official
                        DATA[pretty_name]['owner'] = owner
                        DATA[pretty_name]['repository'] = repo_name
                        # DATA[pretty_name]['versions'] = versions
                        # DATA[pretty_name]['stars'] = stars
                        DATA[pretty_name]['dependents'] = dependents


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


def test_mp_page(name: str) -> tuple[bool, str | None]:
    """
    Test if the marketplace page of an Action is accessible and returns the URL for the data if so.

    :param name: The name of the Action to check.
    :return: True and the URL of the GitHub page if the marketplace page is accessible. Otherwise returns False, None.
    """
    url = f"https://github.com/marketplace/actions/{name}"

    request = get_request("test_name", url)

    if request:
        root = beautiful_html(request.text)
        url = root.xpath('//h5[text()="\n          Links\n         "]/following-sibling::a[1]/@href')
        if url:
            return True, url[0]
        return False, None
    return False, None


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


def get_official(url: str) -> bool:
    """
    Determine if it is an "official" GitHub action.

    :param url: The URL used to determine if it is an Action developed by GitHub or not.
    :return: True if it is a GitHub Action and False otherwise.
    """
    return "/actions/" in url


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


def get_api(key: str, owner: str, repo_name: str) -> int | list:
    """
    Contaxt the API to fetch information.

    :param key: The kind of data to retrieve.
    :param owner: The owner of the repository.
    :param repo_name: The name of the repository.
    :return: An integer or a list, depending of the nature of the needed information.
    """
    urls = {
        'versions': f"https://api.github.com/repos/{owner}/{repo_name}/releases?per_page=100&page=1",
        'stars': f"https://api.github.com/repos/{owner}/{repo_name}/stargazers?per_page=100&page=1",
    }
    to_extract = {
        'versions': 'tag_name',
        'stars': 'login',
    }
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'accept': 'application/vnd.github.v3+json',
    }

    final = []
    api_call = requests.get(urls[key], headers=headers)

    if 'next' not in api_call.links.keys():
        temp = extract(api_call, to_extract[key])
        for extracted in temp:
            final.append(extracted)
    elif 'next' in api_call.links.keys():
        while 'next' in api_call.links.keys():
            temp = extract(api_call, to_extract[key])
            for extracted in temp:
                final.append(extracted)
            api_call = requests.get(api_call.links['next']['url'], headers)
        temp = extract(api_call, to_extract[key])
        for extracted in temp:
            final.append(extracted)

    if key == 'stars':
        return len(final)

    return final


def extract(api_call: requests.Response, to_extract: str) -> list:
    """
    Extract the information from the API.

    :param api_call: The call to the API.
    :param to_extract: The information we need to extract.
    :return: The extracted information in a list.
    """
    extracted = []
    if api_call.status_code == 200:
        for needed in api_call.json():
            extracted.append(needed[to_extract])
    elif api_call.status_code == 403:
        if 'Retry-After' in api_call.headers.keys():
            time.sleep(int(api_call.headers['Retry-After']))
        else:
            reset = int(api_call.headers['X-RateLimit-Reset'])
            current = int(time.time())
            time_for_reset = reset - current
            time.sleep(time_for_reset)

    return extracted


def get_dependents(owner: str, repo_name: str) -> int:
    """
    Get the number of dependents for a repository.

    :param owner: The owner of the repository.
    :param repo_name: The name of the repository.
    :return: The number of dependents.
    """
    url = f"https://github.com/{owner}/{repo_name}/network/dependents"
    xpath = '//*[@id="dependents"]/div[3]/div[1]/div/div/a[1]/text()'

    request = get_request("get_dependents", url)

    root = beautiful_html(request.text)
    ugly_dependents = root.xpath(xpath)[1]
    dependents = int(re.findall(re.compile(r'\d+'), ugly_dependents)[0])

    return dependents


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
        session = requests.Session()
        session.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")

        run_categories = config.get_categories['run']
        if run_categories:
            get_categories()

        """
        Main steps of the code. Retrieves the data.
        """
        run_fetch_data = config.fetch_data['run']
        if run_fetch_data:
            fetch_data_multithread()

            with open("actions_data.json", 'w') as f:
                json.dump(DATA, f, sort_keys=True, indent=4)

            number_of_actions = len(DATA.keys())

            logging.info(f"Number of fetched actions: {number_of_actions}")
        else:
            logging.info(f"Number of fetched actions: N/A")

        session.close()

    logging.info(f"--- {time.time() - start_time} seconds ---")
