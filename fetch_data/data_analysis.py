"""
This script is used to generate plots in order to analyse the data previously retrieved.
"""
from collections import Counter
from datetime import datetime
from fetch_data import request_to_api, get_request, beautiful_html, get_remaining_api_calls, GITHUB_TOKENS
from packaging import version as packaging_version

import data_analysis_config as config
import json
import math
import matplotlib.pyplot as plt
import random
import re
import requests
import seaborn
import statistics
import threading
import time


def market_growing_over_time(p_category: str = None) -> None:
    """
    Shows the plots for the number of actions for each category. The last plot show the global number of actions.

    :param p_category: A string representing the category to plot.
    """
    old_files = config.old_files_names
    actions_data = []
    try:
        for temp_file in old_files:
            with open(temp_file, 'r') as x:
                actions_data.append(json.load(x))
    except FileNotFoundError:
        print(f"File not found. Please, check if the file is located in the same folder as this script.")

    actions_data.append(loaded_data)

    if p_category:
        i = 0
        for data_set in actions_data:
            temp = {}
            for action in data_set:
                if data_set[action]["category"] == p_category:
                    temp[action] = data_set[action]
            actions_data[i] = temp
            i += 1

    grow = {
        "10/03/2022": 0,
        "25/03/2022": 0,
        "13/04/2022": 0,
        "29/04/2022": 0,
        "16/05/2022": 0,
        "17/05/2022": 0,
    }
    grow_keys = list(grow.keys())

    for i in range(len(actions_data)):
        key = grow_keys[i]
        data = actions_data[i]
        grow[key] = len(data)

    values = [grow[k] for k in grow_keys]

    if not p_category:
        show_bar_plots(grow_keys, values, "v", "Growing of All Categories")

    else:
        show_bar_plots(grow_keys, values, "v", f"Growing of \"{p_category}\"")


def show_bar_plots(x: list, y: list, orient: str, title: str) -> None:
    """
    Shows a bar plot.

    :param x: The values for the x axis.
    :param y: The values for the y axis.
    :param orient: The plot orientation.
    :param title: The title of the plot.
    """
    bar_plot = seaborn.barplot(x=x, y=y, orient=orient)
    bar_plot.bar_label(bar_plot.containers[0])
    bar_plot.set(title=title)
    plt.show()


def compute_actions_per_categories() -> list:
    """
    Compute the number of actions for each category.

    :return: A list containing the number of action for each category. The list is sorted in the some order as the
    categories.
    """
    actions_per_categories_n = {}
    for p_category in categories:
        number = 0
        for action in loaded_data:
            if loaded_data[action]["category"] == p_category:
                number += 1
        actions_per_categories_n[p_category] = number

    values = [actions_per_categories_n[k] for k in categories]

    return values


def actions_diversity() -> None:
    """
    Show the plot that represent the diversity of the actions.
    """
    values = compute_actions_per_categories()

    show_bar_plots(values, categories, "h", "Actions Diversity")

    plt.show()


def most_commonly_proposed() -> None:
    """
    Shows the number of categories that falls in each section.
    """
    sections_categories = {
        "> 700": 0,
        "> 550": 0,
        "> 400": 0,
        "> 250": 0,
        "> 100": 0,
        ">= 0": 0,
    }

    for number in actions_per_categories:
        if number > 700:
            sections_categories["> 700"] += 1
        elif number > 550:
            sections_categories["> 550"] += 1
        elif number > 400:
            sections_categories["> 400"] += 1
        elif number > 250:
            sections_categories["> 250"] += 1
        elif number > 100:
            sections_categories["> 100"] += 1
        else:
            sections_categories[">= 0"] += 1

    show_bar_plots(list(sections_categories.keys()), list(sections_categories.values()), "v",
                   "Number of Actions For Each Category")


def actions_technical_lag() -> None:
    """
    Determine the mean for the technical lag of the Actions.
    """
    # versions = get_sample("versions")
    versions = [loaded_data[key]["versions"] for key in loaded_data]
    versions = sort_dates_keys(versions)

    major_mean_days = []
    minor_mean_days = []
    micro_mean_days = []
    for item in versions:
        first_key = list(item.keys())[0]
        try:
            last_major = packaging_version.parse(item[first_key]).major
            last_minor = packaging_version.parse(item[first_key]).minor
            last_micro = packaging_version.parse(item[first_key]).micro
        except AttributeError:
            continue

        major_updates = []
        minor_updates = []
        micro_updates = []

        if last_major > 0:
            major_updates.append(first_key)
        if last_minor > 0:
            minor_updates.append(first_key)
        if last_micro > 0:
            micro_updates.append(first_key)
        for version_date in item:
            try:
                a = packaging_version.parse(item[version_date])
                if a.micro != last_micro:
                    micro_updates.append(version_date)
                    last_micro = a.micro
                if a.minor != last_minor:
                    minor_updates.append(version_date)
                    last_minor = a.minor
                if a.major != last_major:
                    major_updates.append(version_date)
                    last_major = a.major
            except AttributeError:
                continue

        major = days_between_dates(major_updates)
        minor = days_between_dates(minor_updates)
        micro = days_between_dates(micro_updates)

        for element in major:
            major_mean_days.append(element)
        for element in minor:
            minor_mean_days.append(element)
        for element in micro:
            micro_mean_days.append(element)

    print(round(statistics.mean(major_mean_days), 2))
    print(round(statistics.mean(minor_mean_days), 2))
    print(round(statistics.mean(micro_mean_days), 2))


def get_sample(key: str) -> list:
    """
    Returns a sample using a specific key.

    :param key: The key to access the data. Must be a string.
    :return: A list containing the data.
    """
    sample_size = compute_sample_size(len(loaded_data))
    versions = []

    data = loaded_data

    while sample_size > 0:
        random_index = random.randint(0, len(data)-1)
        versions.append(list(data.values())[random_index][key])
        data.pop(list(data.keys())[random_index])
        sample_size -= 1

    return versions


def compute_sample_size(population_size: int) -> int:
    """
    Compute the sample size for a population.

    :param population_size: The total size of the population.
    :return: The sample size.
    """
    sample_for_infinite_population = (1.96 ** 2) * 0.5 * (1 - 0.5) / (0.05 ** 2)
    sample_size = sample_for_infinite_population / (1 + ((sample_for_infinite_population - 1) / population_size))
    sample_size = math.ceil(sample_size)

    return sample_size


def sort_dates_keys(versions: list) -> list:
    """
    Sort the dates for each version.

    :param versions: The list representing the sample of versions.
    :return: The sorted list of versions.
    """
    i = 0
    for dictionary in versions:
        dictionary_keys = list(dictionary.keys())
        dates = [datetime.strptime(dk, "%d/%m/%Y") for dk in dictionary_keys]
        dates.sort()
        sorted_dates = [datetime.strftime(dk, "%d/%m/%Y") for dk in dates]
        temp = {}
        for date in sorted_dates:
            temp[date] = dictionary[date]
        versions[i] = temp
        i += 1

    return versions


def days_between_dates(dates: list) -> list:
    """
    Determine the days between dates placed in a list.

    :param dates: A list with the dates.
    :return: The list of days between the dates in the list.
    """
    i = 0
    j = 1

    days = []
    while j < len(dates):
        difference = abs(datetime.strptime(dates[i], "%d/%m/%Y") - datetime.strptime(dates[j], "%d/%m/%Y"))
        days.append(difference.days)
        i += 1
        j += 1

    return days


def determine_popularity() -> None:
    """
    Determine the popularity of an Action.
    The popularity is computed as number of stars + number of dependents + number of forks + number of watching.
    """
    scores = {}
    for action in loaded_data:
        stars = loaded_data[action]["stars"]
        dependents = loaded_data[action]["dependents"]["number"]
        forks = loaded_data[action]["forks"]
        watching = loaded_data[action]["watching"]
        score = stars + dependents + forks + watching

        scores[action] = score

    scores_counter = Counter(scores)

    for key, value in scores_counter.most_common(15):
        key_category = loaded_data[key]["category"]
        print(f"{key}: {value} --- {key_category}")


def multiple_actions_start_threads():
    threads = 10
    run_threads = []
    multiple_results = [None] * threads

    data = loaded_data
    full = int(len(data) / (threads-1))
    elements = {}

    index = 0

    count = 0
    for element in data:
        if count == full:
            run_threads.append(threading.Thread(target=multiple_actions, args=(elements, multiple_results, index,)))
            elements = {}
            count = 0
            index += 1
        if count < full:
            elements[element] = data[element]
            count += 1

    run_threads.append(threading.Thread(target=multiple_actions, args=(elements, multiple_results, index,)))

    for thread in run_threads:
        thread.start()
    for thread in run_threads:
        thread.join()

    return multiple_results


def multiple_actions(p_elements: dict, results, index) -> None:
    """
    Check the mean for the number of actions per repository. Safe the links to yml files.

    :param p_elements: The dictionary with the Actions in it.
    """
    actions_in_repos = []
    yml_files = []

    i = 0
    for action in p_elements:
        actions = 0

        owner = p_elements[action]["owner"]
        repository = p_elements[action]["repository"]
        url = f"https://github.com/{owner}/{repository}"

        request = get_request("multiple_actions", url)

        xpath_branch = '//span[@class="css-truncate-target"]/text()'

        try:
            root = beautiful_html(request.text)
        except AttributeError:
            continue

        space_pattern = re.compile(r"\s+")
        main_branch = re.sub(space_pattern, "", root.xpath(xpath_branch)[0])

        api_branch_url = f"https://api.github.com/repos/{owner}/{repository}/commits/{main_branch}"
        tree_response = request_to_api(api_branch_url, i)
        while True:
            if tree_response.status_code == 200:
                tree_json = tree_response.json()
                tree_sha = tree_json["commit"]["tree"]["sha"]
                break
            elif tree_response.status_code == 403:
                tree_response, i = deal_with_api_403(tree_response, i, api_branch_url)

        api_files_main_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{tree_sha}"
        files_response = request_to_api(api_files_main_url, i)
        github_url = ""
        while True:
            if files_response.status_code == 200:
                files_json = files_response.json()
                files = files_json["tree"]
                for element in files:
                    if ".yml" in element["path"]:
                        yml_files.append((element["path"], element["url"]))
                        actions += 1
                    elif ".github" == element["path"]:
                        github_sha = element["sha"]
                        github_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{github_sha}"
                break
            elif files_response.status_code == 403:
                files_response, i = deal_with_api_403(files_response, i, api_files_main_url)

        workflow_url = ""
        if github_url:
            github_response = request_to_api(github_url, i)
            while True:
                if github_response.status_code == 200:
                    github_json = github_response.json()
                    for element in github_json["tree"]:
                        if element["path"] == "workflows":
                            workflow_url = element["url"]
                        if ".yml" in element["path"]:
                            yml_files.append((element["path"], element["url"]))
                            actions += 1
                    break
                elif github_response.status_code == 403:
                    github_response, i = deal_with_api_403(github_response, i, github_url)
                else:
                    break

        if workflow_url:
            workflow_response = request_to_api(workflow_url, i)
            while True:
                if workflow_response.status_code == 200:
                    workflow_json = workflow_response.json()
                    for element in workflow_json["tree"]:
                        if ".yml" in element["path"]:
                            yml_files.append((element["path"], element["url"]))
                            actions += 1
                    break
                elif workflow_response.status_code == 403:
                    workflow_response, i = deal_with_api_403(workflow_response, i, workflow_url)

        actions_in_repos.append(actions)

    results[index] = (actions_in_repos, yml_files)
    # print(round(statistics.mean(actions_in_repos), 2))
    # with open("yml_files.json", 'w') as f2:
    #     json.dump(yml_files, f2, indent=4)


def deal_with_api_403(api_response: requests.Response, i: int, url: str) -> tuple[requests.Response, int]:
    """
    Deal with a response when it gets error 403. Wait until it gets a 200 status code.

    :param api_response: The response.
    :param i: The index for the GitHub Tokens.
    :param url: The URL to connect to.
    :return: The response and the index for the GitHub tokens.
    """
    message = 'message' in api_response.json().keys()
    if 'Retry-After' in api_response.headers.keys():
        while not get_remaining_api_calls():
            time.sleep(30)
        i = (i + 1) % len(GITHUB_TOKENS)
    elif message and "Authenticated requests get a higher rate limit." in api_response.json()['message']:
        pass
    else:
        reset = int(api_response.headers['X-RateLimit-Reset'])
        current = int(time.time())
        time_for_reset = reset - current
        if time_for_reset > 0:
            while not get_remaining_api_calls():
                time.sleep(30)
            else:
                i = (i + 1) % len(GITHUB_TOKENS)

    tree_response = request_to_api(url, i)

    return tree_response, i


def check_issues():
    """
    Check the number of repositories with open and closed issues.
    """
    open_issues = 0
    closed_issues = 0

    open_up_to_date = 0
    open_not_up_to_date = 0

    for action in loaded_data:
        if loaded_data[action]["issues"]["open"] > 0:
            open_issues += 1

            dates = [key for key in loaded_data[action]["versions"]]
            dates = [datetime.strptime(date, "%d/%m/%Y") for date in dates]
            dates.sort()
            sorted_dates = [datetime.strftime(date, "%d/%m/%Y") for date in dates]
            last_date = sorted_dates[-1]
            now = datetime.strftime(datetime.now(), "%d/%m/%Y")
            difference = datetime.strptime(now, "%d/%m/%Y") - datetime.strptime(last_date, "%d/%m/%Y")
            days = difference.days
            if days > 182:
                open_not_up_to_date += 1
            else:
                open_up_to_date += 1
        elif loaded_data[action]["issues"]["closed"] > 0:
            closed_issues += 1

    print(open_issues, closed_issues)
    print(open_up_to_date, open_not_up_to_date)


if __name__ == "__main__":
    file = config.file_name
    try:
        with open(file, 'r') as f:
            loaded_data = json.load(f)
    except FileNotFoundError:
        print("File not found. Please, check if the file is located in the same folder as this script.")

    categories = ['api-management', 'chat', 'code-quality', 'code-review', 'continuous-integration',
                  'dependency-management', 'deployment', 'ides', 'learning', 'localization', 'mobile', 'monitoring',
                  'project-management', 'publishing', 'recently-added', 'security', 'support', 'testing', 'utilities']

    if config.market_growing_over_time:
        for category in categories:
            market_growing_over_time(category)
        market_growing_over_time()

    if config.actions_diversity or config.most_commonly_proposed:
        actions_per_categories = compute_actions_per_categories()

    if config.actions_diversity:
        actions_diversity()

    if config.most_commonly_proposed:
        most_commonly_proposed()

    if config.actions_technical_lag:
        actions_technical_lag()

    if config.popularity:
        determine_popularity()

    if config.multiple_actions:
        results = multiple_actions_start_threads()
        print(results)

    if config.actions_issues:
        check_issues()
