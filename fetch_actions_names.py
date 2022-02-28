"""
This script identify the actions with a valid marketplace page.
"""

from bs4 import BeautifulSoup
from html import unescape
from lxml import html

import fetch_actions_names_config as conf
import logging
import numpy
import re
import requests
import threading
import time


def get_categories() -> list:
    """
    Return the list of GitHub Actions categories.

    :return: A list with the GitHub Actions categories as strings.
    """
    return_categories = []
    session = requests.Session()
    url = "https://github.com/marketplace?type=actions"
    request = session.get(url)

    soup = BeautifulSoup(request.text, 'html.parser')
    pretty_soup = soup.prettify()
    root = html.fromstring(pretty_soup)
    result = root.xpath('//*[@id="js-pjax-container"]/div[2]/div[1]/nav/ul[2]/li/a/text()')
    pattern = re.compile(r'[^a-zA-Z ]')
    for li in result:
        return_categories.append(re.sub(re.compile(r" {2,}"), '', re.sub(pattern, '', li).lower()).replace(' ', '-'))

    session.close()

    return return_categories


def get_names_of_actions() -> None:
    """
    Fetching the names of Actions.
    """
    global names
    global categories

    for category in categories:
        logging.info(f">>> Fetching Actions for category '{category}' <<<")
        max_page_number = get_page_index(category)

        number_of_threads = get_number_of_threads(max_page_number)

        threads = []

        for i in range(0, number_of_threads):
            list_of_pages = [x for x in range(1, max_page_number + 1) if x % number_of_threads == i]
            threads.append(threading.Thread(target=fetch_names, args=(list_of_pages, category,), name=f"thread_{i}"))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    logging.info(f"Number of Actions: {len(names)}")


def get_page_index(category: str) -> int:
    """
    Fetching the index. This index is used to identify the number of pages on the GitHub Actions marketplace.

    :param category: The category we are interested of knowing the number of pages.
    :return: The higher page number.
    """
    start_index = conf.get_page_index["start_index"]
    try:
        index = int(start_index)
    except ValueError:
        logging.error("Bad index in configuration file.\nBad value is " + start_index)
        index = 49
    logging.info("Start index: " + str(index))

    page_number = get_max_page(category)
    logging.info("Number of pages: " + str(page_number))

    return page_number


def get_max_page(category: str) -> int:
    """
    Get the number of the last page. It is useful to know it for multithreading.

    :param category: The category we are interested of knowing the number of pages.
    :return: The number of the last page.
    """
    session = requests.Session()
    url = f"https://github.com/marketplace?category={category}&page=1&type=actions"
    request = session.get(url)

    while request.status_code != 200:
        if request.status_code == 429:
            logging.info("get_max_page - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 1)
            logging.info("get_max_page - sleeping finished")
        request = session.get(url)

    page_xpath_0 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/a[not(@class="next_page")]'
    page_xpath_1 = '//*[@id="js-pjax-container"]/div[2]/div[1]/div[3]/div/em'
    page_xpath = f'{page_xpath_0} | {page_xpath_1}'
    soup = BeautifulSoup(request.text, 'html.parser')
    pretty_soup = soup.prettify()
    root = html.fromstring(pretty_soup)
    numbers = root.xpath(page_xpath)
    last_index = len(numbers) - 1
    if last_index > 0:
        max_page = re.sub(re.compile(r"\s{2,}"), '', numbers[last_index].text)
        session.close()
        return int(max_page)

    else:
        return 0


def get_number_of_threads(max_page_number: int) -> int:
    """
    Fetching the number of threads to use. These threads are going to be used in order to determine the index.

    :param max_page_number: The number of pages on the GitHub marketplace.
    :return: The number of threads to use.
    """
    num_of_threads = conf.get_page_index["threads"]
    try:
        num_of_threads = int(num_of_threads)
        # the point here is not to allow more threads then the number of pages
        if num_of_threads > max_page_number:
            num_of_threads = max_page_number
        elif num_of_threads < 1:
            num_of_threads = 1
    except ValueError:
        logging.error("Bad number of threads in configuration file.\nBad value is " + num_of_threads)
        num_of_threads = 5
    logging.info("Number of threads: " + str(num_of_threads))

    return num_of_threads


def fetch_names(pages: list, category: str) -> None:
    """
    Get the actions names from GitHub marketplace.

    :param pages: The list of pages on which fetch the actions names
    :param category: The category of GitHub Actions.
    """
    global names

    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    session = requests.Session()

    for page in pages:
        url = f"https://github.com/marketplace?category={category}&page={page}&query=&type=actions"

        request = session.get(url)

        while request.status_code != 200:
            if request.status_code == 429:
                logging.info("fetch_names - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
                time.sleep(int(request.headers["Retry-After"]) + 1)
                logging.info("fetch_names - sleeping finished")
            request = session.get(url)

        actions_names = actions_names_pattern_compiled.findall(request.text)
        for j in range(0, len(actions_names)):
            actions_names[j] = actions_names[j].split('<h3 class="h4">')[1].split('</h3>')[0].lower()
            actions_names[j] = unescape(actions_names[j])  # convert html code to utf-8 ex: &quot -> "
            actions_names[j] = actions_names[j].replace(" - ", "-").replace(" ", "-")
            actions_names[j] = re.sub("[^0-9a-zA-Z_-]", "-", actions_names[j])
            while re.search("^-.*$", actions_names[j]):
                actions_names[j] = actions_names[j][1:]
            while re.search("^.*-$", actions_names[j]):
                actions_names[j] = actions_names[j][:-1]
            actions_names[j] = re.sub("-{2,}", "-", actions_names[j])
            if actions_names[j] not in names:
                names.append(actions_names[j])

    session.close()


def do_name_verification() -> None:
    """
    Verifications of names of Actions. Some marketplace page of Actions are not accessible.
    Only start 10 threads because there is a limit of 100 requests per minutes on the GitHub marketplace.
    """
    threads = []

    num_of_threads = 10
    for i in range(0, num_of_threads):
        list_of_names = [names[x] for x in range(0, len(names)) if x % num_of_threads == i]
        threads.append(threading.Thread(target=test_names, args=(list_of_names,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def test_names(p_names: list) -> None:
    """
    Test if the Marketplace page of Actions is accessible.

    :param p_names: List of names of Actions.
    """
    session = requests.Session()
    for name in p_names:
        url = f"https://github.com/marketplace/actions/{name}"
        request = session.get(url)
        while request.status_code == 429:
            logging.info("test_names - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 1)
            logging.info("test_names - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
            request = session.get(url)
        if request.status_code == 404:
            logging.info(f"The Action '{name}' don't have a marketplace page.")
            names.remove(name)

    session.close()


if __name__ == "__main__":
    start_time = time.time()

    """
    Logging config
    """
    log_file_name = "fetch_actions_names.log"
    logging.basicConfig(filename=log_file_name, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')

    execute_names_of_actions = conf.get_names_of_actions["execute"]
    if execute_names_of_actions:
        categories = get_categories()

        names = []
        get_names_of_actions()

        name_verification = conf.name_verification
        if name_verification:
            do_name_verification()
            logging.info(f"Number of accessible actions: {len(names)}")
        else:
            logging.info(f"Number of accessible actions: N/A")

        save_names = numpy.array(names)
        numpy.save("names_of_actions", save_names)

    logging.info(f"--- {time.time() - start_time} seconds ---")
    # np.load("test.npy").tolist()
