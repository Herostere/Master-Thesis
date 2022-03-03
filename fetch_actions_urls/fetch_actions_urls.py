"""
Identify the urls of the GitHub Actions on the marketplace.
"""
from bs4 import BeautifulSoup
from lxml import html

import fetch_actions_urls_config as config
import logging
import numpy
import os
import requests
import threading
import time


def fetch_urls() -> None:
    """
    Starts the threads for the fetching of the urls.
    """
    max_threads = config.max_threads
    threads = []

    for i in range(0, max_threads):
        list_of_actions = [names[x] for x in range(0, len(names)) if x % max_threads == i]
        threads.append(threading.Thread(target=get_urls, args=(list_of_actions,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def get_urls(list_of_actions: list) -> None:
    """
    Fetch the urls on the marketplace page.

    :param list_of_actions: The list of names of Actions to gather urls.
    """
    global urls

    print(len(list_of_actions))
    for action in list_of_actions:
        url = f"https://github.com/marketplace/actions/{action}"
        print(url)
        session, request = get_request("get_urls", url)

        soup = BeautifulSoup(request.text, 'html.parser')
        pretty_soup = soup.prettify()
        root = html.fromstring(pretty_soup)
        result = root.xpath('//*[@id="js-pjax-container"]/div/div/div[3]/aside/div[4]/a[1]/@href')
        urls.append(result)
        print(len(urls))

        session.close()


# This code is duplicate from fetch_actions_names to resolve an issue when importing the function.
def get_request(function: str, url: str) -> tuple[requests.Session, requests.Response]:
    """
    Create a session and get a webpage with a status code of 200.

    :param function: The name of the calling function.
    :param url: The url to connect to.
    :return: The session and the response with status code 200.
    """
    session = requests.Session()
    request = session.get(url)

    while request.status_code != 200:
        print(request.status_code)
        if request.status_code == 429:
            logging.info(f"{function} - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 1)
            logging.info(f"{function} - sleeping finished")
        request = session.get(url)

    return session, request


if __name__ == "__main__":
    start_time = time.time()

    """
    Logging config
    """
    log_file_name = "fetch_actions_urls.log"
    logging.basicConfig(filename=log_file_name, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')

    """
    Starting fetching
    """
    run = config.run
    if run:
        current_path = os.path.realpath(__file__)
        current_directory = os.path.dirname(current_path)
        actions_names_directory = current_directory.replace("fetch_actions_urls", "fetch_actions_names")
        file_with_names = os.path.join(actions_names_directory, "names_of_actions.npy")
        names = numpy.load(file_with_names)

        urls = []

        fetch_urls()
        save = numpy.array(urls)

        numpy.save("urls_of_actions", save)

    logging.info(f"--- {time.time() - start_time} seconds ---")
