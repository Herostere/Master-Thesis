from html import unescape

import logging
import re
import requests
import threading
import time


def get_max_page(from_index: int = 1) -> int:
    """
    Get the number of the last page. It is useful to know it for multithreading.

    :param from_index: The page index to start from.
    :return: The number of the last page.
    """
    session = requests.Session()
    k = from_index
    url = f"https://github.com/marketplace?page={k}&query=&type=actions"
    request = session.get(url)
    found = False
    while request.status_code == 200 or request.status_code == 429:
        if request.status_code == 429:
            logging.info("get_max_page - sleeping " + str(int(request.headers["Retry-After"]) + 1) + " seconds")
            time.sleep(int(request.headers["Retry-After"]) + 1)
            logging.info("get_max_page - sleeping finished")
        k += 1
        url = f"https://github.com/marketplace?page={k}&query=&type=actions"
        request = session.get(url)

        if not found:
            found = True
    if found:
        session.close()
        return k - 1
    session.close()
    if from_index == 0:
        logging.error("No page found for Actions... Weird.")
        exit()
    return get_max_page(int(from_index / 2))


# TODO
def get_categories() -> list:
    """
    Return the list of GitHub Actions categories.

    :return: A list with the GitHub Actions categories as strings.
    """
    session = requests.Session()
    url = "https://github.com/marketplace?category=&type=actions"
    request = session.get(url)

    return []


def fetch_names(pages: list) -> None:
    """
    Get the actions names from GitHub marketplace.

    :param pages: The list of pages on which fetch the actions names
    """
    global names

    actions_names_pattern = '<h3 class="h4">.*</h3>'
    actions_names_pattern_compiled = re.compile(actions_names_pattern)

    session = requests.Session()

    for page in pages:
        url = f"https://github.com/marketplace?page={page}&query=&type=actions"

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


def test_names(p_names):
    test_session = requests.Session()
    for name in p_names:
        url = f"https://github.com/marketplace/actions/{name}"
        test_request = test_session.get(url)
        while test_request.status_code == 429:
            time.sleep(int(test_request.headers["Retry-After"]) + 1)
            test_request = test_session.get(url)
        if test_request.status_code == 404:
            logging.info(f"The Action '{name}' don't have a marketplace page.")
            names.remove(name)

    test_session.close()


if __name__ == "__main__":
    log_file_name = "fetch_actions_names.log"
    logging.basicConfig(filename=log_file_name, level=logging.INFO, filemode='w', format='%(asctime)s %(message)s')

    while True:
        try:
            index = int(input("From index > "))
            break
        except ValueError:
            index = int(input("Enter a correct value for the index > "))
    logging.info("Index input by user: " + str(index))

    max_page_number = get_max_page(index)
    logging.info("Number of pages: " + str(max_page_number))

    while True:
        try:
            number_of_threads = int(input("Number of threads to use > "))
            # the point here is not to allow more threads then the number of pages
            if number_of_threads > max_page_number:
                number_of_threads = max_page_number
            elif number_of_threads < 1:
                number_of_threads = 1
            break
        except ValueError:
            number_of_threads = int(input("Enter a correct value for the number of threads to use > "))
    logging.info("Number of threads: " + str(number_of_threads))

    start_time = time.time()

    threads = []

    for i in range(0, number_of_threads):
        list_of_pages = [x for x in range(1, max_page_number + 1) if x % number_of_threads == i]
        threads.append(threading.Thread(target=fetch_names, args=(list_of_pages,), name=f"thread_{i}"))

    names = []

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    threads = []

    logging.info(f"Number of Actions: {len(names)}")

    number_of_threads = 10
    for i in range(0, number_of_threads):
        list_of_names = [names[x] for x in range(0, len(names)) if x % number_of_threads == i]
        threads.append(threading.Thread(target=test_names, args=(list_of_names,)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    logging.info(f"Number of accessible actions: {len(names)}")

    print(f"--- {time.time() - start_time} seconds ---")
