"""
This script is used to generate plots in order to analyse the data previously retrieved.
"""
from collections import Counter
from datetime import datetime
from fetch_data import (
    request_to_api,
    get_request,
    beautiful_html,
    get_remaining_api_calls,
    GITHUB_TOKENS)
from packaging import version as packaging_version

import base64
import data_analysis_config as config
import json
import math
import matplotlib.pyplot as plt
import numpy
import random
import re
import requests
import seaborn
import statistics
import threading
import time
import yaml
import yaml.constructor
import yaml.parser
import yaml.scanner


def market_growing_over_time(p_category: str = None) -> None:
    """
    Shows the plots for the number of actions for each category. The last plot show the global number of actions.

    :param p_category: The category for to be plotted.
    """
    old_files = config.old_files_names
    actions_data = []
    try:
        for temp_file in old_files:
            with open(temp_file, 'r', encoding='utf-8') as old_data:
                actions_data.append(json.load(old_data))
    except FileNotFoundError:
        print("File not found. Please, check if the path.")

    actions_data.append(loaded_data)

    if p_category:
        for i, data_set in enumerate(actions_data):
            temp = {}
            for action in data_set:
                if data_set[action]["category"] == p_category:
                    temp[action] = data_set[action]
            actions_data[i] = temp

    grow_keys = list(grow.keys())

    for i, action_data in enumerate(actions_data):
        key = grow_keys[i]
        data = action_data
        grow[key] = len(data)

    values = [grow[k] for k in grow_keys]

    if not p_category:
        show_bar_plots(grow_keys, values, "v", "Growing of All Categories")

    else:
        show_bar_plots(grow_keys, values, "v", f"Growing of \"{p_category}\"")


def show_bar_plots(x_axis: list, y_axis: list, orient: str, title: str) -> None:
    """
    Show a bar plot.

    :param x_axis: The list of values for the x axis.
    :param y_axis: The list of values for the y axis.
    :param orient: The plot orientation.
    :param title: The title of the plot.
    """
    bar_plot = seaborn.barplot(x=x_axis, y=y_axis, orient=orient, color="steelblue")
    bar_plot.bar_label(bar_plot.containers[0])
    bar_plot.set(title=title)
    for elem in bar_plot.patches:
        x_position = elem.get_x()
        width = elem.get_width()
        center = x_position + width / 2

        new_width = width / 1.5
        elem.set_width(new_width)
        elem.set_x(center - new_width / 2)
    plt.show()


def compute_actions_per_categories() -> list:
    """
    Compute the number of actions for each category.

    :return: A list containing the number of action for each category. The list is sorted in the some order as the
    categories.
    """
    actions_per_categories_list = []
    for p_category in categories:
        number = 0
        for action in loaded_data:
            if loaded_data[action]["category"] == p_category:
                number += 1
        actions_per_categories_list.append(number)

    return actions_per_categories_list


def actions_diversity() -> None:
    """
    Show the plot that represent the diversity of the actions.
    """
    print(max(actions_per_categories))
    print(round(statistics.mean(actions_per_categories)))
    show_bar_plots(actions_per_categories, categories, "h", "Actions Diversity")


def most_commonly_proposed() -> None:
    """
    Shows the number of categories that falls in each section.
    Sections are:
        - > 700
        - > 550
        - > 400
        - > 250
        - > 100
        - >= 0
    """
    sections_categories = {
        "> 700": 0,
        "> 550": 0,
        "> 400": 0,
        "> 250": 0,
        "> 100": 0,
        ">= 0": 0,
    }

    categories_700 = ""
    categories_550 = ""
    categories_400 = ""
    categories_250 = ""
    categories_100 = ""
    categories_0 = ""

    for i, number in enumerate(actions_per_categories):
        if number > 700:
            sections_categories["> 700"] += 1
            categories_700 += f"{categories[i]}, "
        elif number > 550:
            sections_categories["> 550"] += 1
            categories_550 += f"{categories[i]}, "
        elif number > 400:
            sections_categories["> 400"] += 1
            categories_400 += f"{categories[i]}, "
        elif number > 250:
            sections_categories["> 250"] += 1
            categories_250 += f"{categories[i]}, "
        elif number > 100:
            sections_categories["> 100"] += 1
            categories_100 += f"{categories[i]}, "
        else:
            sections_categories[">= 0"] += 1
            categories_0 += f"{categories[i]}, "

    show_bar_plots(list(sections_categories.keys()), list(sections_categories.values()), "v",
                   "Number of Actions For the Categories")

    print(f'The categories "{categories_700[:-2]}" have more than 700 actions.')
    print(f'The categories "{categories_550[:-2]}" have more than 550 actions.')
    print(f'The categories "{categories_400[:-2]}" have more than 400 actions.')
    print(f'The categories "{categories_250[:-2]}" have more than 250 actions.')
    print(f'The categories "{categories_100[:-2]}" have more than 100 actions.')
    print(f'The categories "{categories_0[:-2]}" have more than 0 actions.')


def actions_technical_lag() -> None:
    """
    Determine the technical lag of the Actions.
    """
    versions = list(loaded_data[action]["versions"] for action in loaded_data)
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
                current_version = packaging_version.parse(item[version_date])
                if current_version.major != last_major:
                    major_updates.append(version_date)
                    last_major = current_version.major
                    last_minor = current_version.minor
                    last_micro = current_version.micro
                elif current_version.minor != last_minor:
                    minor_updates.append(version_date)
                    last_minor = current_version.minor
                    last_micro = current_version.micro
                elif current_version.micro != last_micro:
                    micro_updates.append(version_date)
                    last_micro = current_version.micro
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

    print(statistics.median(major_mean_days))
    print(f"Number of days between major versions (mean): {round(statistics.mean(major_mean_days))}")
    print(numpy.percentile(major_mean_days, 25))
    print(numpy.percentile(major_mean_days, 75))
    print("-" * 10)
    print(statistics.median(minor_mean_days))
    print(f"Number of days between minor versions (mean): {round(statistics.mean(minor_mean_days))}")
    print(numpy.percentile(minor_mean_days, 25))
    print(numpy.percentile(minor_mean_days, 75))
    print("-" * 10)
    print(statistics.median(micro_mean_days))
    print(f"Number of days between patch versions (mean): {round(statistics.mean(micro_mean_days))}")
    print(numpy.percentile(micro_mean_days, 25))
    print(numpy.percentile(micro_mean_days, 75))
    print("-" * 10)


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
    for i, dictionary in enumerate(versions):
        dictionary_keys = list(dictionary.keys())
        dates = [datetime.strptime(dk, "%d/%m/%Y") for dk in dictionary_keys]
        dates.sort()
        sorted_dates = [datetime.strftime(dk, "%d/%m/%Y") for dk in dates]
        versions[i] = {}
        for date in sorted_dates:
            versions[i][date] = dictionary[date]

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


def actions_popularity(printing: bool = False) -> dict:
    """
    Determine the popularity of the Actions.
    The popularity is computed as the number of stars + number of dependents + number of forks + number of watching.

    :param printing: True if the function should print the output. Otherwise False.
    :return: The list of most popular Actions.
    """
    scores = {}
    for action in loaded_data:
        stars = loaded_data[action]["stars"]
        dependents = loaded_data[action]["dependents"]["number"]
        forks = loaded_data[action]["forks"]
        watching = loaded_data[action]["watching"]
        score = stars + dependents + forks + watching

        owner = loaded_data[action]["owner"]
        repository = loaded_data[action]["repository"]

        scores[f"{owner}/{repository}"] = score

    sample_size = compute_sample_size(len(scores))
    popular_actions = Counter(scores).most_common(sample_size)

    popular_actions_dictionary = {}
    for key, value in popular_actions:
        popular_actions_dictionary[key] = value

    if printing:
        for i, element in enumerate(popular_actions_dictionary):
            value = popular_actions_dictionary[element]
            print(f'{i+1}: "{element}" -> {value}')

    return popular_actions_dictionary


def ymls_content_start_threads() -> None:
    """
    Starts the threads for the sample of yml files.
    """
    threads = 10
    run_threads = []
    multiple_results = [[]] * threads

    data = get_actions_sample(False)
    full = int(len(data) / (threads-1))  # How much data must be handled by each thread but the last one.
    elements = {}

    index = 0
    count = 0

    for element in data:
        if count == full:
            run_threads.append(threading.Thread(target=ymls_content, args=(elements, multiple_results, index,)))
            elements = {}
            count = 0
            index += 1
        if count < full:
            elements[element] = data[element]
            count += 1

    run_threads.append(threading.Thread(target=ymls_content, args=(elements, multiple_results, index,)))

    for thread in run_threads:
        thread.start()
    for thread in run_threads:
        thread.join()

    ymls = []
    for action in multiple_results:
        for dependent in action:
            ymls.append(dependent)

    with open('outputs/ymls_contents.json', 'w', encoding='utf-8') as yml_file:
        json.dump(ymls, yml_file, indent=4)


def ymls_content(p_elements: dict, p_results: list, index: int) -> None:
    """
    Fetch the content of yml files.

    :param p_elements: The dictionary with the Actions in it.
    :param p_results: The list in which the data must be saved.
    :param index: The position in the list where the data must be saved.
    """
    ymls_total = []
    for action in p_elements:
        dependents_url = p_elements[action]["dependents"]["package_url"]
        dependents_number = p_elements[action]["dependents"]["number"]
        if dependents_number != 0:
            sample_dependents = get_sample_dependents(dependents_url, dependents_number)
            ymls = get_ymls(sample_dependents)
            ymls_total += ymls

    p_results[index] = ymls_total


def get_sample_dependents(url: str, dependents_number: int) -> list:
    """
    Go a sample of dependents for an Action.

    :param url: The URL where the dependents can be retrieved.
    :param dependents_number: The number of dependents on this URL.
    :return: The sample of dependents.
    """
    request = get_request("get_sample_dependents", url)

    try:
        root = beautiful_html(request.text)
    except AttributeError:
        return []

    dependents_xpath = '//div[@class="Box-row d-flex flex-items-center"]//a[@data-hovercard-type="repository"]/@href'
    next_page_xpath = f'//a[contains("\n             Next\n            ", text()) and @class = "btn btn-outline BtnGroup-item"]//@href'
    last_page_xpath = f'//div[@class="BtnGroup"]/button[contains("\n             Next\n            ", text())]'

    root_dependents = root.xpath(dependents_xpath)
    if not root_dependents:
        return []

    sample_size = dependents_number
    if dependents_number > 388:
        sample_size = compute_sample_size(dependents_number)

    probability = sample_size / dependents_number

    sample = []
    page = root
    rounds = 25
    while len(sample) < sample_size and rounds > 0:
        dependents = page.xpath(dependents_xpath)
        for dependent in dependents:
            random_value = random.random()
            to_add = "https://github.com" + dependent
            if random_value < probability and to_add not in sample:
                sample.append(to_add)

        last_page = len(page.xpath(last_page_xpath)) == 1
        if last_page:
            page = root
        else:
            try:
                next_page = page.xpath(next_page_xpath)[0]
                request = get_request("get_dependents_sample", next_page)
            except IndexError:
                rounds -= 1
            try:
                page = beautiful_html(request.text)
            except AttributeError:
                page = root

        rounds -= 1

    return sample


def get_ymls(actions: list) -> list:
    """
    Get the content of yml files.

    :param actions: The list of actions.
    :return: A list of lists. Each sub list contains de ymls for a dependent of the action.
    """
    to_return = []

    i = 0
    for element in actions:
        request = get_request("get_ymls", element)
        try:
            root = beautiful_html(request.text)
        except AttributeError:
            continue

        owner = element.split("//")[1].split("/")[1]
        repository = element.split("//")[1].split("/")[2]

        xpath_branch = '//span[@class="css-truncate-target"]/text()'
        space_pattern = re.compile(r'\s+')
        main_branch = re.sub(space_pattern, "", root.xpath(xpath_branch)[0])

        api_branch_url = f'https://api.github.com/repos/{owner}/{repository}/commits/{main_branch}'
        tree_response, i = deal_with_api(api_branch_url, i)
        if tree_response:
            tree_sha = tree_response.json()["commit"]["tree"]["sha"]
        else:
            continue

        api_files_main_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{tree_sha}"
        files_response = request_to_api(api_files_main_url, i)
        github_url = ""
        while True:
            if files_response.status_code == 200:
                files_json = files_response.json()
                files = files_json["tree"]
                for p_file in files:
                    if ".github" == p_file["path"]:
                        github_sha = p_file["sha"]
                        github_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{github_sha}"
                        break
                break
            if files_response.status_code == 403:
                files_response, i = deal_with_api_403(files_response, i, api_files_main_url)
            else:
                break

        workflow_url = ""
        if github_url:
            github_response = request_to_api(github_url, i)
            while True:
                if github_response.status_code == 200:
                    github_json = github_response.json()
                    for p_file in github_json["tree"]:
                        if p_file["path"] == "workflows":
                            workflow_url = p_file["url"]
                            break
                    break
                if github_response.status_code == 403:
                    github_response, i = deal_with_api_403(github_response, i, github_url)
                else:
                    break

        ymls_files = []
        if workflow_url:
            workflow_response = request_to_api(workflow_url, i)
            while True:
                if workflow_response.status_code == 200:
                    workflow_json = workflow_response.json()
                    for p_file in workflow_json["tree"]:
                        if ".yml" in p_file["path"] or ".yaml" in p_file["path"]:
                            content_response = request_to_api(p_file["url"], i)
                            while True:
                                if content_response.status_code == 200:
                                    content_json = content_response.json()
                                    tried = 0
                                    try:
                                        content = content_json['content']
                                        ymls_files.append(content)
                                    except KeyError:
                                        content_response, i = deal_with_api_403(content_response, i, p_file['url'])
                                        if tried == 1:
                                            break
                                        tried += 1
                                if content_response.status_code == 403:
                                    content_response, i = deal_with_api_403(content_response, i, p_file['url'])
                                else:
                                    break
                    break
                if workflow_response.status_code == 403:
                    workflow_response, i = deal_with_api_403(workflow_response, i, workflow_url)
                else:
                    break
        to_return.append(ymls_files)

    return to_return


def deal_with_api(url, i) -> tuple[requests.Response, int] | tuple[None, int]:
    """
    Make the request to the api and deal with the response.

    :param url: The url to connect to.
    :param i: The GITHUB_TOKENS index.
    :return: The response or none, with the next index for the GITHUB_TOKEN.
    """
    response = request_to_api(url, i)
    while True:
        if response.status_code == 200:
            return response, i
        elif response.status_code == 403:
            response, i = deal_with_api_403(response, i, url)
        else:
            return None, i


def deal_with_api_403(api_response: requests.Response, i: int, url: str) -> tuple[requests.Response, int]:
    """
    Deal with a response when it gets error 403. Wait until it gets a 200 status code.

    :param api_response: The response.
    :param i: The index for the GitHub Tokens.
    :param url: The URL to connect to.
    :return: The response and the index for the GitHub tokens in a tuple.
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
            i = (i + 1) % len(GITHUB_TOKENS)

    tree_response = request_to_api(url, i)

    return tree_response, i


def actions_issues() -> None:
    """
    Check the number of repositories with open and closed issues.
    """
    open_issues = 0
    closed_issues = 0
    open_no_close_issues = 0
    closed_no_open_issues = 0
    no_issues = 0

    open_up_to_date = 0
    open_not_up_to_date = 0

    open_ones = []
    closed_ones = []

    open_but_closed = []
    closed_but_open = []

    open_more_182 = []
    open_less_182 = []

    for action in loaded_data:
        number_of_open_issues = loaded_data[action]["issues"]["open"]
        number_of_closed_issues = loaded_data[action]["issues"]["closed"]

        open_ones.append(number_of_open_issues)
        closed_ones.append(number_of_closed_issues)

        if number_of_open_issues > 0 and number_of_closed_issues == 0:
            open_no_close_issues += 1
            open_but_closed.append(number_of_open_issues)
        elif number_of_closed_issues > 0 and number_of_open_issues == 0:
            closed_no_open_issues += 1
            closed_but_open.append(number_of_closed_issues)
        elif number_of_open_issues == 0 and number_of_closed_issues == 0:
            no_issues += 1

        if number_of_open_issues > 0:
            open_issues += 1
            dates = list(loaded_data[action]["versions"])
            dates = [datetime.strptime(date, "%d/%m/%Y") for date in dates]
            dates.sort()
            sorted_dates = [datetime.strftime(date, "%d/%m/%Y") for date in dates]
            last_update = sorted_dates[-1]
            now = datetime.strftime(datetime.now(), "%d/%m/%Y")
            difference = datetime.strptime(now, "%d/%m/%Y") - datetime.strptime(last_update, "%d/%m/%Y")
            days_since_update = difference.days
            if days_since_update > 223:
                open_not_up_to_date += 1
                open_more_182.append(number_of_open_issues)
            else:
                open_up_to_date += 1
                open_less_182.append(number_of_open_issues)

        if number_of_closed_issues > 0:
            closed_issues += 1

    number_of_actions = len(loaded_data)

    print('-' * 10 + " Open")
    print(f"Actions with open issues: {open_issues}/{number_of_actions}.")
    print(f"Median of open issues for actions: {statistics.median(open_ones)}.")
    print(f"Mean of open issues for actions: {round(statistics.mean(open_ones))}.")
    print(f"q1 of open issues for actions: {numpy.percentile(open_ones, 25)}.")
    print(f"q3 of open issues for actions: {numpy.percentile(open_ones, 75)}.")
    print()

    print('-' * 10 + " Only open")
    print(f"Actions with only open ones: {open_no_close_issues}/{number_of_actions}.")
    print(f"Median Actions with only open: {statistics.median(open_but_closed)}.")
    print(f"Mean Actions with only open: {round(statistics.mean(open_but_closed))}.")
    print(f"q1 Actions with only open: {numpy.percentile(open_but_closed, 25)}.")
    print(f"q3 Actions with only open: {numpy.percentile(open_but_closed, 75)}.")
    print()

    print('-' * 10 + " Close")
    print(f"Actions with closed issues: {closed_issues}/{number_of_actions}.")
    print(f"Median of closed issues for actions: {statistics.median(closed_ones)}.")
    print(f"Mean of closed issues for actions: {round(statistics.mean(closed_ones))}.")
    print(f"q1 of closed issues for actions: {numpy.percentile(closed_ones, 25)}.")
    print(f"q3 of closed issues for actions: {numpy.percentile(closed_ones, 75)}.")
    print()

    print('-' * 10 + " Only closed")
    print(f"Actions with only closed ones: {closed_no_open_issues}/{number_of_actions}.")
    print(f"Median Actions with only closed: {statistics.median(closed_but_open)}.")
    print(f"Mean Actions with only closed: {round(statistics.mean(closed_but_open))}.")
    print(f"q1 Actions with only closed: {numpy.percentile(closed_but_open, 25)}.")
    print(f"q3 Actions with only closed: {numpy.percentile(closed_but_open, 75)}.")
    print()

    print('-' * 10 + " No issues")
    print(f"Actions without issues: {no_issues}/{number_of_actions}.")
    print()

    print('-' * 10 + " > 223")
    print(f"Actions with open issue and last update more than 223 days ago: {open_not_up_to_date}.")
    print()

    print('-' * 10 + " < 223")
    print(f"Actions with open issue and last update less than 223 days ago: {open_up_to_date}.")


def most_active_contributors() -> tuple[list, list]:
    """
    Retrieve the most active contributors.

    :return: A tuple with the list of most common contributor with bots, and without bots.
    """
    contributors = {}
    for action in loaded_data:
        action_contributors = loaded_data[action]["contributors"]
        for contributor in action_contributors:
            if contributor not in contributors:
                contributors[contributor] = 1
            else:
                contributors[contributor] += 1

    sample_size = compute_sample_size(len(contributors))
    contributors_counter = Counter(contributors)
    most_common_with_bots = contributors_counter.most_common(10)

    contributors_to_delete = [contributor for contributor in contributors
                              if "-bot" in contributor or "[bot]" in contributor]
    for contributor in contributors_to_delete:
        del contributors[contributor]

    contributors_counter = Counter(contributors)
    most_common_without_bots = contributors_counter.most_common(10)

    print(f"Most active contributors (bots included):")
    for contributor, contributions in most_common_with_bots:
        print(f"    - {contributor} - {contributions}")

    print(f"\nMost active contributors (bots excluded):")
    for contributor, contributions in most_common_without_bots:
        print(f"    - {contributor} - {contributions}")

    popular = actions_popularity()
    for contributor, _ in most_common_without_bots:
        in_it = False
        count = 0
        for action in popular:
            if contributor in loaded_data[action]['contributors']:
                in_it = True
                count += 1
        print(in_it, count)

    return most_common_with_bots, most_common_without_bots


def compare_number_actions_officials_not_officials() -> None:
    """
    Check the number of actions developed by official and not officials users.
    """
    popular_actions_ = actions_popularity()
    popular_actions = {}
    for action in popular_actions_:
        popular_actions[action] = loaded_data[action]

    not_popular_officials = []
    not_popular_not_officials = []
    for i in range(samples_to_make):
        not_popular_actions = get_actions_sample(True)
        not_popular_official_or_not = compute_official_or_not(not_popular_actions)
        not_popular_officials.append(not_popular_official_or_not["official"])
        not_popular_not_officials.append(not_popular_official_or_not["unofficial"])

    full_official_or_not = compute_official_or_not(loaded_data)
    popular_official_or_not = compute_official_or_not(popular_actions)
    not_popular_officials = math.ceil(statistics.mean(not_popular_officials))
    not_popular_not_officials = math.ceil(statistics.mean(not_popular_not_officials))

    print(f'Full: {full_official_or_not["official"]} officials - {full_official_or_not["unofficial"]} unofficial.')
    print(f'Popular: {popular_official_or_not["official"]} officials - '
          f'{popular_official_or_not["unofficial"]} unofficial.')
    print(f'Not popular: {not_popular_officials} officials - '
          f'{not_popular_not_officials} unofficial.')


def compute_official_or_not(data: dict) -> dict:
    official_or_not = {
        "official": 0,
        "unofficial": 0,
    }

    for action in data:
        if not data[action]["verified"]:
            official_or_not["official"] += 1
        else:
            official_or_not["unofficial"] += 1

    return official_or_not


def how_actions_triggered() -> None:
    """
    Check how the actions are triggered on a general basis. Take a representative sample of the most popular actions.
    """
    try:
        with open("outputs/ymls_contents.json", 'r', encoding='utf-8') as json_file:
            ymls_content_json = json.load(json_file)
    except FileNotFoundError:
        print("The file if the content of the yml files is not accessible.")
        exit()

    how_triggered = {}

    for sample in ymls_content_json:
        for content in sample:
            try:
                content_decoded = base64.b64decode(content).decode("utf-8").replace("on:", "trigger:")
                content_decoded = content_decoded.replace('"on":', "trigger:")
                content_decoded = yaml.safe_load(content_decoded)
                triggers_on = content_decoded["trigger"]
            except (yaml.constructor.ConstructorError, yaml.scanner.ScannerError, yaml.parser.ParserError):
                continue
            except (TypeError, KeyError, UnicodeDecodeError):
                continue
            if isinstance(triggers_on, str):
                if triggers_on not in how_triggered:
                    how_triggered[triggers_on] = 1
                else:
                    how_triggered[triggers_on] += 1
            else:
                for trigger in triggers_on:
                    if trigger not in how_triggered:
                        how_triggered[trigger] = 1
                    else:
                        how_triggered[trigger] += 1

    keys = list(how_triggered.keys())
    values = list(how_triggered.values())
    # show_bar_plots(values, keys, 'h', "How Actions are Triggered")

    print(sum(values))
    print(len(how_triggered))
    most_common = Counter(how_triggered).most_common()
    triggered_times = []
    for element in most_common:
        print(element)
        triggered_times.append(element[1])

    print(statistics.median(triggered_times))
    print(round(statistics.mean(triggered_times)))
    print(numpy.percentile(triggered_times, 25))
    print(numpy.percentile(triggered_times, 75))


def multiple_actions() -> None:
    """
    Get the number of actions used by a sample of projects.
    """
    try:
        with open("outputs/ymls_contents.json", 'r', encoding='utf-8') as json_file:
            ymls_content_json = json.load(json_file)
    except FileNotFoundError:
        print("The file if the content of the yml files is not accessible.")
        exit()

    used = {}
    actions_used_by_projects = []
    for sample in ymls_content_json:
        counter = 0
        uses = []
        for content in sample:
            try:
                decoded_content = base64.b64decode(content).decode("utf-8").replace("on:", "trigger:")
            except UnicodeDecodeError:
                continue
            decoded_content = decoded_content.replace('"on":', "trigger:")
            list_decoded_content = decoded_content.split('\n')
            for element in list_decoded_content:
                stripped_element = element.replace('uses : ', 'uses: ')
                stripped_element = stripped_element.strip().replace('- uses:', 'uses:')
                comment = False
                if stripped_element:
                    comment = stripped_element[0] == '#'
                if not comment and "uses" in stripped_element[:4] and stripped_element not in uses:
                    use = stripped_element.split("uses: ")[1]
                    if "@" in use:
                        use = use.split('@')[0]
                    counter += 1
                    uses.append(use)
        actions_used_by_projects.append(counter)
        for using in uses:
            if using not in used:
                used[using] = 1
            else:
                used[using] += 1

    most_used = Counter(used).most_common(10)
    for action in most_used:
        print(f'{action[0]}: {action[1]}')
        print(loaded_data[action[0]]['verified'])

    print(f'Median: {statistics.median(actions_used_by_projects)}')
    print(f'Mean: {round(statistics.mean(actions_used_by_projects), 2)}')
    print(f'q1: {numpy.percentile(actions_used_by_projects, 25)}')
    print(f'q3: {numpy.percentile(actions_used_by_projects, 75)}')


def compare_number_of_versions() -> None:
    """
    Compare the number of versions for popular and not popular actions.
    """
    popular_actions = actions_popularity()

    not_popular_versions = []
    for i in range(samples_to_make):
        not_popular_actions = get_actions_sample(True)
        not_popular_versions_ = [len(not_popular_actions[action]["versions"]) for action in not_popular_actions]
        not_popular_versions += not_popular_versions_

    popular_versions = [len(loaded_data[action]["versions"]) for action in popular_actions]
    actions_versions = [len(loaded_data[action]["versions"]) for action in loaded_data]

    print('-' * 10 + ' popular')
    print(statistics.median(popular_versions))
    print(round(statistics.mean(popular_versions)))
    print(numpy.percentile(popular_versions, 25))
    print(numpy.percentile(popular_versions, 75))

    print('-' * 10 + ' not popular')
    print(statistics.median(not_popular_versions))
    print(round(statistics.mean(not_popular_versions)))
    print(numpy.percentile(not_popular_versions, 25))
    print(numpy.percentile(not_popular_versions, 75))

    print('-' * 10 + ' overall')
    print(statistics.median(actions_versions))
    print(round(statistics.mean(actions_versions)))
    print(numpy.percentile(actions_versions, 25))
    print(numpy.percentile(actions_versions, 75))


def compare_number_of_contributors() -> None:
    """
    Compare the number of contributors.
    """
    popular_actions = actions_popularity()

    popular_actions_contributors = [len(loaded_data[action]["contributors"]) for action in popular_actions]
    not_popular_actions_contributors = []

    for i in range(samples_to_make):
        not_popular_actions = get_actions_sample(True)
        not_popular_actions_contributors_temp = [len(not_popular_actions[action]["contributors"])
                                                 for action in not_popular_actions]
        not_popular_actions_contributors += not_popular_actions_contributors_temp

    actions_contributors = [len(loaded_data[action]["contributors"]) for action in loaded_data]

    print('-' * 10 + ' popular')
    print(statistics.median(popular_actions_contributors))
    print(round(statistics.mean(popular_actions_contributors)))
    print(numpy.percentile(popular_actions_contributors, 25))
    print(numpy.percentile(popular_actions_contributors, 75))

    print('-' * 10 + ' not popular')
    print(statistics.median(not_popular_actions_contributors))
    print(round(statistics.mean(not_popular_actions_contributors)))
    print(numpy.percentile(not_popular_actions_contributors, 25))
    print(numpy.percentile(not_popular_actions_contributors, 75))

    print('-' * 10 + ' overall')
    print(statistics.median(actions_contributors))
    print(round(statistics.mean(actions_contributors)))
    print(numpy.percentile(actions_contributors, 25))
    print(numpy.percentile(actions_contributors, 75))


def do_actions_use_dependabot() -> None:
    """
    Show the number of actions that use dependabot.
    """
    popular_actions = actions_popularity()
    popular_use_dependabot = 0

    for action in popular_actions:
        contributors = loaded_data[action]["contributors"]
        if "dependabot[bot]" in contributors:
            popular_use_dependabot += 1

    not_popular_use_dependabot = []
    for i in range(samples_to_make):
        sample_not_popular_actions = get_actions_sample(True)

        not_popular_use_dependabot_ = 0
        for action in sample_not_popular_actions:
            contributors = loaded_data[action]["contributors"]
            if "dependabot[bot]" in contributors:
                not_popular_use_dependabot_ += 1

        not_popular_use_dependabot.append(not_popular_use_dependabot_)

    sample_size = len(not_popular_use_dependabot)
    mean_not_popular_use_dependabot = math.ceil(statistics.mean(not_popular_use_dependabot))

    total_popular_actions = len(popular_actions)
    print(f"{popular_use_dependabot}/{total_popular_actions} popular actions are using dependabot.")
    print(f"{mean_not_popular_use_dependabot}/{sample_size} not popular actions are using dependabot.")

    actions_using_dependabot = 0
    for action in loaded_data:
        contributors = loaded_data[action]["contributors"]
        if "dependabot[bot]" in contributors:
            actions_using_dependabot += 1

    print(f"{actions_using_dependabot}/{len(loaded_data)} actions are using dependabot.")


def get_actions_sample(exclude_popular: bool) -> dict:
    """
    Get a representative sample of the Actions.

    :param exclude_popular: If true, the sample does not contains popular actions.
    :return: The representative sample of the Actions.
    """
    popular_actions = actions_popularity()

    total_number_actions = len(loaded_data)
    sample_size = compute_sample_size(total_number_actions)

    sample = {}
    probability = round(sample_size / total_number_actions, 16)
    total_sample = len(sample)

    while total_sample < sample_size:
        for action in loaded_data:
            random_number = random.random()
            if exclude_popular and random_number < probability and action not in popular_actions:
                sample[action] = loaded_data[action]
            elif random_number < probability:
                sample[action] = loaded_data[action]
            total_sample = len(sample)
            if total_sample == sample_size:
                break

    return sample


if __name__ == "__main__":
    file = config.file_name
    try:
        with open(file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
    except FileNotFoundError:
        print("File not found. Please, check if the file is located in the same folder as this script.")

    categories = ['api-management', 'chat', 'code-quality', 'code-review', 'continuous-integration',
                  'dependency-management', 'deployment', 'ides', 'learning', 'localization', 'mobile', 'monitoring',
                  'project-management', 'publishing', 'recently-added', 'security', 'support', 'testing', 'utilities']

    samples_to_make = config.samples_to_make

    if config.market_growing_over_time:
        grow = config.grow

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

    if config.actions_popularity:
        actions_popularity(True)

    if config.ymls_content:
        ymls_content_start_threads()

    if config.multiple_actions:
        multiple_actions()

    if config.actions_issues:
        actions_issues()

    if config.most_active_contributors:
        most_active_contributors()

    if config.compare_number_actions_officials_not_officials:
        compare_number_actions_officials_not_officials()

    if config.how_actions_triggered:
        how_actions_triggered()

    if config.compare_number_of_versions:
        compare_number_of_versions()

    if config.compare_number_of_contributors:
        compare_number_of_contributors()

    if config.do_actions_use_dependabot:
        do_actions_use_dependabot()
