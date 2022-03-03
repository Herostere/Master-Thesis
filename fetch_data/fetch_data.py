"""
This script identify the actions with a valid marketplace page.
"""
from bs4 import BeautifulSoup
from html import unescape
from lxml import html

import fetch_data_config as config
import logging
import numpy
import re
import requests
import threading
import time


def get_categories() -> None:
    """
    Save the list of GitHub Actions categories as a numpy array.
    """
    save_categories = []
    url = "https://github.com/marketplace?type=actions"

    session, request = get_request("get_categories", url)

    root = beautiful_html(request.text)
    session.close()

    result = root.xpath('//*[@id="js-pjax-container"]/div[2]/div[1]/nav/ul[2]/li/a/text()')

    pattern = re.compile(r'[^a-zA-Z ]')
    for li in result:
        category = re.sub(re.compile(r" {2,}"), '', re.sub(pattern, '', li).lower()).replace(' ', '-')
        save_categories.append(category)

    save_categories = numpy.array(save_categories)
    numpy.save("categories.npy", save_categories)


def get_request(function: str, url: str) -> tuple[requests.Session, requests.Response] | tuple[None, None]:
    """
    Create a session and get a webpage with a status code of 200.

    :param function: The name of the calling function.
    :param url: The url to connect to.
    :return: The session and the response with status code 200. If error 404, returns (None, None).
    """
    session = requests.Session()
    request = session.get(url)

    while request.status_code != 200:
        if request.status_code == 429:
            logging.info(f"{function} - sleeping " + str(int(request.headers["Retry-After"]) + 0.3) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 0.3)
            logging.info(f"{function} - sleeping finished")
        if request.status_code == 404:
            session.close()
            return None, None
        request = session.get(url)

    return session, request


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


def fetch_data() -> None:
    """
    Retrieve information about each Action.
    """
    categories = numpy.load("categories.npy")

    for category in categories:
        max_page_number = get_max_page(category)

        number_of_threads = get_number_of_threads(max_page_number)

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
    start_index = config.fetch_data["start_index"]
    try:
        index = int(start_index)
    except ValueError:
        logging.error("Bad index in configuration file.\nBad value is " + start_index)
        index = 49  # arbitrary because it looks like there is a maximum of 50 pages by category on the MP.
    logging.info("Start index: " + str(index))

    url = f"https://github.com/marketplace?category={category}&page=1&type=actions"

    session, request = get_request("get_max_page", url)

    page_xpath_0 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/a[not(@class="next_page")]'
    page_xpath_1 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/em'
    page_xpath = f'{page_xpath_0} | {page_xpath_1}'

    root = beautiful_html(request.text)
    numbers = root.xpath(page_xpath)
    last_index = len(numbers) - 1

    if last_index > 0:
        max_page = re.sub(re.compile(r"\s{2,}"), '', numbers[last_index].text)
        session.close()
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
    global actions_names

    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    for page in pages:
        url = f"https://github.com/marketplace?category={category}&page={page}&query=&type=actions"
        session, request = get_request("fetch_names", url)

        actions_names_ugly = actions_names_pattern_compiled.findall(request.text)
        session.close()

        # Below is used to format the name as in the marketplace urls.
        for j in range(0, len(actions_names_ugly)):
            actions_names_ugly[j] = format_action_name(actions_names_ugly[j])

            if actions_names_ugly[j] not in actions_names:
                mp_page, url = test_mp_page(actions_names_ugly[j])
                if mp_page:
                    if test_link(url):
                        actions_names = numpy.append(actions_names, actions_names_ugly[j])


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

    session, request = get_request("test_name", url)

    if request:
        session.close()
        root = beautiful_html(request.text)
        url = root.xpath('//*[@id="js-pjax-container"]/div/div/div[3]/aside/div[4]/a[1]/@href')
        if url:
            return True, url[0]
        return False, None
    return False, None


def test_link(url: str) -> bool:
    """
    Test if a link is valid.

    :param url: The URL to check.
    :return: True if the URL is accessible. Otherwise False.
    """
    session, request = get_request("test_link", url)

    if request:
        session.close()
        return True
    return False


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
    run = config.run
    if run:
        """
        Fetch the categories.
        """
        run_categories = config.get_categories['run']
        if run_categories:
            get_categories()

        """
        Main steps of the code. Retrieves the data.
        """
        run_fetch_data = config.fetch_data['run']
        if run_fetch_data:
            actions_names = []

            fetch_data()

            actions_names = numpy.array(actions_names)
            numpy.save("names_of_actions", actions_names)
            logging.info(f"Number of accessible actions: {actions_names.shape[0]}")
        else:
            logging.info(f"Number of accessible actions: N/A")

    logging.info(f"--- {time.time() - start_time} seconds ---")
