"""
This script identify the actions with a valid marketplace page.

You will need to use Python3.10.
"""
from bs4 import BeautifulSoup
from datetime import datetime
from html import unescape
from lxml import html, etree
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


GITHUB_TOKENS = config.tokens
LIMIT = config.limit_requests
SESSION = requests.Session()
SESSION.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")
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

    if config.override_save_categories["run"]:
        save_categories = config.override_save_categories["categories"]
        save_categories = numpy.array(save_categories)

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
    global SESSION

    while True:
        try:
            request = SESSION.get(url)
            break
        except requests.ConnectionError:
            SESSION.close()
            SESSION = requests.Session()
            SESSION.cookies['user_session'] = os.getenv("CONNECTION_COOKIE")

            threads = max(10, number_of_threads)
            adapter = requests.adapters.HTTPAdapter(pool_connections=threads, pool_maxsize=threads)
            SESSION.mount("https://", adapter)
            SESSION.mount("http://", adapter)
            # return get_request(function, url)
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
    global number_of_threads
    categories = numpy.load("categories.npy")

    logging.info("Fetching the data")

    for category in categories:
        try:
            with open("outputs/actions_data.json", 'r') as f1:
                save_data = json.load(f1)
        except FileNotFoundError:
            save_data = json.loads('{}')

        logging.info(f"***** {category} *****")

        max_page_number = get_max_page(category)

        number_of_threads = get_number_of_threads(max_page_number)

        adapter = requests.adapters.HTTPAdapter(pool_connections=number_of_threads, pool_maxsize=number_of_threads)
        SESSION.mount("https://", adapter)
        SESSION.mount("http://", adapter)

        threads = []

        if number_of_threads > 0:
            for i in range(0, number_of_threads):
                list_of_pages = [x for x in range(1, max_page_number + 1) if x % number_of_threads == i]
                threads.append(threading.Thread(target=thread_data,
                                                args=(list_of_pages, category, save_data,),
                                                name=f"thread_{i}"))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        with open("outputs/actions_data.json", 'w') as f2:
            json.dump(save_data, f2, sort_keys=True, indent=4)


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


def thread_data(pages: list, category: str, save_data: dict) -> None:
    """
    For each Action on a category:
        - Check if it has a valid MP page.
        - If so, check if it has a valid link to a github page.
        - If so, get some data about it.

    :param pages: The list of pages on which fetch the actions names.
    :param category: The category of GitHub Actions.
    :param save_data: The JSON data.
    """
    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    index = 0

    for page in pages:
        url = f"https://github.com/marketplace?category={category}&page={page}&query=&type=actions"

        request = get_request("fetch_names", url)

        actions_names_ugly = actions_names_pattern_compiled.findall(request.text)

        # Below is used to format the name as in the marketplace urls.
        for j in range(0, len(actions_names_ugly)):
            action_name = format_action_name(actions_names_ugly[j])
            mp_page, url = test_mp_page(action_name)
            if mp_page:
                owner = get_owner(url)
                repo_name = get_repo_name(url)
                pretty_name = f'{owner}/{repo_name}'
                already_fetched = save_data.keys()
                if pretty_name in already_fetched and save_data[pretty_name]["category"] == "recently-added":
                    if category != "recently-added":
                        save_data[pretty_name]["category"] = category
                elif pretty_name not in already_fetched:
                    data = test_link(url)
                    if data:
                        save_data[pretty_name] = {}
                        save_data[pretty_name]['category'] = category
                        verified = get_verified(mp_page)
                        save_data[pretty_name]['verified'] = verified
                        save_data[pretty_name]['owner'] = owner
                        save_data[pretty_name]['repository'] = repo_name
                        save_data[pretty_name]['name'] = format_action_name(actions_names_ugly[j])

                        if config.fetch_categories["versions"]:
                            versions, index = get_api('versions', owner, repo_name, index)
                            save_data[pretty_name]['versions'] = versions

                        if config.fetch_categories["dependents"]:
                            dependents = get_dependents(owner, repo_name)
                            save_data[pretty_name]['dependents'] = {}
                            save_data[pretty_name]['dependents']['number'] = dependents[0]
                            save_data[pretty_name]['dependents']['package_url'] = dependents[1]

                        if config.fetch_categories["contributors"]:
                            contributors, index = get_api('contributors', owner, repo_name, index)
                            contributors.sort()
                            save_data[pretty_name]['contributors'] = contributors

                        stars = config.fetch_categories["stars"]
                        watchers = config.fetch_categories["watchers"]
                        forks = config.fetch_categories["forks"]
                        if stars or watchers or forks:
                            get_from_repo_api = ['stargazers_count', 'subscribers_count', 'forks_count']
                            stars_watching_forks, index = get_api(get_from_repo_api, owner, repo_name, index)
                            if stars:
                                stars = int(stars_watching_forks['stargazers_count'])
                                save_data[pretty_name]['stars'] = stars
                            if watchers:
                                watching = int(stars_watching_forks['subscribers_count'])
                                save_data[pretty_name]['watching'] = watching
                            if forks:
                                forks = int(stars_watching_forks['forks_count'])
                                save_data[pretty_name]['forks'] = forks

                        if config.fetch_categories["issues"]:
                            issues, index = get_api("issues", owner, repo_name, index)
                            save_data[pretty_name]["issues"] = {}
                            try:
                                save_data[pretty_name]["issues"]["open"] = issues["open"]
                                save_data[pretty_name]["issues"]["closed"] = issues["closed"]
                            except KeyError:
                                print(pretty_name)


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


def test_mp_page(name: str) -> tuple[requests.Response, str] | tuple[None, None]:
    """
    Test if the marketplace page of an Action is accessible and returns the URL for the data if so.

    :param name: The name of the Action to check.
    :return: The response and the URL of the GitHub page if the marketplace page is accessible.
             Otherwise returns None, None.
    """
    url = f"https://github.com/marketplace/actions/{name}"

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


def get_api(key: str | list, owner: str, repo_name: str, index: int) -> tuple[int | list | dict, int]:
    """
    Contact the API to fetch information.

    :param key: The kind of data to retrieve.
    :param owner: The owner of the repository.
    :param repo_name: The name of the repository.
    :param index: The index for the list of Tokens.
    :return: A tuple with an integer, a list or a dictionary, depending of the nature of the needed information and
             the index for the next API call.
    """
    i = index
    queries = {"versions": "releases(first: 100) { totalCount edges { cursor node { tag { name } createdAt } } }"}
    query = {'query': f'''
    {{
      repositoryOwner(login: "{owner}") {{
        repository(name: "{repo_name}") {{
          {queries[key]}
        }}
      }}
    }}
    '''}

    api_answer = request_to_api(query, i)
    print(api_answer.json())

    exit()





    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    urls = {
        'versions': f"{url}/releases?per_page=100&page=1",
        'stars': f"{url}/stargazers?per_page=100&page=1",
        'contributors': f"{url}/contributors?per_page=100&page=1",
        'forks': f"{url}/forks?per_page=100&page=1",
        'watching': f"{url}/subscribers?per_page=100&page=1",
        'issues': f"{url}/issues?state=all&per_page=100",
        'files': f"{url}/commits?per_page=100&page=1",
    }
    to_extract = {
        'versions': ('tag_name', 'published_at'),
        'stars': 'login',
        'contributors': 'login',
        'forks': 'id',
        'watching': 'login',
        'issues': ('open', 'closed')
    }

    try:
        is_tuple = type(to_extract[key]) is tuple
    except TypeError:
        is_tuple = False

    if is_tuple:
        final = {}
    else:
        final = []

    if type(key) is list:
        api_call = request_to_api(url, i)
    else:
        api_call = request_to_api(urls[key], i)

    if type(key) is list:
        to_return, i = extract(api_call, key, url, i)
        return to_return.json(), i

    if 'next' not in api_call.links.keys():
        temp, i = extract(api_call, to_extract[key], urls[key], i)
        if is_tuple:
            final = final | temp
        else:
            for extracted in temp:
                final.append(extracted)
    elif 'next' in api_call.links.keys():
        while 'next' in api_call.links.keys():
            temp, i = extract(api_call, to_extract[key], urls[key], i)
            if is_tuple:
                final = final | temp
            else:
                for extracted in temp:
                    final.append(extracted)

            api_call = request_to_api(api_call.links['next']['url'], i)

        temp, i = extract(api_call, to_extract[key], urls[key], i)
        if is_tuple:
            final = final | temp
        else:
            for extracted in temp:
                final.append(extracted)

    if key in ['stars', 'forks', 'watching']:
        return len(final), i

    return final, i


def request_to_api(query: dict, i: int) -> requests.Response:
    """
    Make a request to the GitHub's API.

    :param url: The URL where the information is located.
    :param i: The index for the GitHub Tokens.
    :return: The API response.
    """
    url = "https://api.github.com/graphql"
    headers = {
        'Authorization': f'token {GITHUB_TOKENS[i]}',
    }

    while True:
        try:
            api_call = requests.post(url, json=query, headers=headers)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(60)

    return api_call


def extract(api_call: requests.Response, to_extract: str | tuple | list, url, index):
    """
    Extract the information from the API.

    :param api_call: The call to the API.
    :param to_extract: The information we need to extract.
    :param url: The URL of the API.
    :param index: The index in the list of Tokens.
    :return: The extracted information in a list or dictionary and the index for the API.
    :rtype: tuple[list | dict | requests.Response, int]
    """
    i = index

    is_tuple = type(to_extract) is tuple
    if is_tuple:
        extracted = {}
    else:
        extracted = []

    if api_call.status_code == 200:
        if ('open', 'closed') == to_extract:
            extracted["open"] = 0
            extracted["closed"] = 0
        for needed in api_call.json():
            if type(to_extract) is list:
                return api_call, i
            if is_tuple:
                if ('open', 'closed') == to_extract:
                    if needed['state'] == "closed":
                        extracted["closed"] += 1
                    else:
                        extracted["open"] += 1
                else:
                    key = datetime.strptime(needed[to_extract[1]], '%Y-%m-%dT%H:%M:%SZ').strftime('%d/%m/%Y')
                    value = needed[to_extract[0]]
                    extracted[key] = value
            else:
                extracted.append(needed[to_extract])
    elif api_call.status_code == 403:
        message = 'message' in api_call.json().keys()
        if 'Retry-After' in api_call.headers.keys():
            while not get_remaining_api_calls():
                # now = datetime.now()
                # finish = now + timedelta(seconds=int(api_call.headers['Retry-After']))
                # finish = finish.strftime('%H:%M:%S')
                #
                # logging.info(f"API sleeping {str(int(api_call.headers['Retry-After']))} seconds (finish {finish})")
                # time.sleep(int(api_call.headers['Retry-After']))
                time.sleep(30)
            i = (i + 1) % len(GITHUB_TOKENS)
            logging.info(f"API switching to {i}")
        elif message and "Authenticated requests get a higher rate limit." in api_call.json()['message']:
            pass
        else:
            reset = int(api_call.headers['X-RateLimit-Reset'])
            current = int(time.time())
            time_for_reset = reset - current
            if time_for_reset > 0:
                while not get_remaining_api_calls():
                    # now = datetime.now()
                    # # finish = now + timedelta(seconds=int(api_call.headers['Retry-After']))
                    # finish = now + timedelta(seconds=time_for_reset)
                    # finish = finish.strftime('%H:%M:%S')
                    #
                    # logging.info(f"API sleeping {str(time_for_reset)} seconds (finish {finish})")
                    # time.sleep(time_for_reset)
                    time.sleep(30)
                i = (i + 1) % len(GITHUB_TOKENS)
                logging.info(f"API switching to {i}")
        headers = {
            'Authorization': f'token {GITHUB_TOKENS[i]}',
            'accept': 'application/vnd.github.v3+json',
        }
        api_call = requests.get(url, headers=headers)
        return extract(api_call, to_extract, url, i)

    return extracted, i


def get_remaining_api_calls() -> bool:
    """
    Tells if API calls can be made or not.

    :return: True if there can be API requests. Otherwise, False.
    """
    for token in GITHUB_TOKENS:
        headers = {
            'Authorization': f'token {token}',
            'accept': 'application/vnd.github.v3+json',
        }
        api_call = requests.get("http://api.github.com/rate_limit", headers=headers)
        if int(api_call.headers['X-RateLimit-Remaining']) > 0:
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

            try:
                with open("outputs/actions_data.json", 'r') as f:
                    load_data = json.load(f)
            except FileNotFoundError:
                load_data = json.loads('{}')

            number_of_actions = len(load_data.keys())

            logging.info(f"Number of fetched actions: {number_of_actions}")
        else:
            logging.info(f"Number of fetched actions: N/A")

        SESSION.close()

    logging.info(f"--- {time.time() - start_time} seconds ---")

"""
To compute the sample size:
    1) compute the sample size for an infinite population
    2) adjust the sample size for the finite population
    
    1) s = (z**2) * p * (1 - p) / (m**2) with z = 1.96, p = 0.5 and m = 0.05
    2) s2 = s / (1 + ((s - 1) / population_size))
    
    return math.ceil(s2)
"""