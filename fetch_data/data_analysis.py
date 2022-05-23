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
import random
import re
import requests
import seaborn
import statistics
import threading
import time
import yaml


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

    grow = {
        "10/03/2022": 0,
        "25/03/2022": 0,
        "13/04/2022": 0,
        "29/04/2022": 0,
        "16/05/2022": 0,
        "17/05/2022": 0,
    }
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
    bar_plot = seaborn.barplot(x=x_axis, y=y_axis, orient=orient)
    bar_plot.bar_label(bar_plot.containers[0])
    bar_plot.set(title=title)
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
                if current_version.micro != last_micro:
                    micro_updates.append(version_date)
                    last_micro = current_version.micro
                if current_version.minor != last_minor:
                    minor_updates.append(version_date)
                    last_minor = current_version.minor
                if current_version.major != last_major:
                    major_updates.append(version_date)
                    last_major = current_version.major
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

    print(f"Number of days between major versions (mean): {round(statistics.mean(major_mean_days), 2)}")
    print(f"Number of days between minor versions (mean): {round(statistics.mean(minor_mean_days), 2)}")
    print(f"Number of days between patch versions (mean): {round(statistics.mean(micro_mean_days), 2)}")


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

        scores[f"{owner}/{repository}/{action}"] = score

    sample_size = compute_sample_size(len(scores))
    popular_actions = Counter(scores).most_common(sample_size)

    popular_actions_dictionary = {}
    for key, value in popular_actions:
        popular_actions_dictionary[key] = value

    if printing:
        for i, element in enumerate(popular_actions_dictionary):
            name = element.split("/")[2]
            value = popular_actions_dictionary[element]
            print(f'{i+1}: "{name}" -> {value}')

    return popular_actions_dictionary


def multiple_actions_start_threads() -> tuple[dict, dict]:
    """
    Starts the threads for multiple_actions().

    :return: A tuple with the dictionaries that contains the data.
    """
    threads = 10
    run_threads = []
    multiple_results = [[]] * threads

    data = loaded_data
    full = int(len(data) / (threads-1))  # How much data must be handled by each thread but the last one.
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

    yml_files = [files[1] for files in multiple_results if files is not None]
    yml_per_repository = [files[0] for files in multiple_results if files is not None]
    yml_files = {key: value for dictionary in yml_files for key, value in dictionary.items()}
    yml_per_repository = {key: value for dictionary in yml_per_repository for key, value in dictionary.items()}
    with open("outputs/yml_files.json", 'w', encoding="utf-8") as json_file:
        json.dump(yml_files, json_file, indent=4)
    with open("outputs/yml_per_repository.json", 'w', encoding="utf-8") as json_file:
        json.dump(yml_per_repository, json_file, indent=4)

    return yml_per_repository, yml_files


def multiple_actions(p_elements: dict, p_results: list, index: int) -> None:
    """
    Check if actions are using other actions.

    :param p_elements: The dictionary with the Actions in it.
    :param p_results: The list in which the data must be saved.
    :param index: The position in the list where the data must be saved.
    """
    workflow_actions_used = {}

    # i = 0
    # for action in p_elements:
    #     owner = p_elements[action]["owner"]
    #     repository = p_elements[action]["repository"]
    #     url = f'https://github.com/{owner}/{repository}'
    #
    #     request = get_request("multiple_actions", url)
    #     xpath_branch = '//span[@class="css-truncate-target"]/text()'
    #
    #     try:
    #         root = beautiful_html(request.text)
    #     except AttributeError:
    #         continue
    #
    #     space_pattern = re.compile(r'\s+')
    #     main_branch = re.sub(space_pattern, "", root.xpath(xpath_branch)[0])
    #
    #     api_branch_url = f'https://api.github.com/repos/{owner}/{repository}/commits/{main_branch}'
    #     tree_response, i = deal_with_api(api_branch_url, i)
    #     if tree_response:
    #         tree_sha = tree_response.json()["commit"]["tree"]["sha"]
    #     else:
    #         continue
    #
    #     api_files_main_url = f'https://api.github.com/repos/{owner}/{repository}/git/trees/{tree_sha}'
    #     files_response, i = deal_with_api(api_files_main_url, i)
    #     if files_response:
    #         files = files_response.json()['tree']
    #         for p_file in files:
    #             if 'action.yml' in p_file['path']:
    #
    #
    #     api_files_main_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{tree_sha}"
    #     files_response = request_to_api(api_files_main_url, i)
    #     github_url = ""
    #     while True:
    #         if files_response.status_code == 200:
    #             files_json = files_response.json()
    #             files = files_json["tree"]
    #             for element in files:
    #                 if ".yml" in element["path"]:
    #                     yml_files[f"{owner}/{repository}/{action}"] = element["url"]
    #                     actions += 1
    #                 elif ".github" == element["path"]:
    #                     github_sha = element["sha"]
    #                     github_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{github_sha}"
    #             break
    #         if files_response.status_code == 403:
    #             files_response, i = deal_with_api_403(files_response, i, api_files_main_url)
    #         else:
    #             break
    #
    #     workflow_url = ""
    #     if github_url:
    #         github_response = request_to_api(github_url, i)
    #         while True:
    #             if github_response.status_code == 200:
    #                 github_json = github_response.json()
    #                 for element in github_json["tree"]:
    #                     if element["path"] == "workflows":
    #                         workflow_url = element["url"]
    #                     if ".yml" in element["path"]:
    #                         yml_files[f"{owner}/{repository}/{action}"] = element["url"]
    #                         actions += 1
    #                 break
    #             if github_response.status_code == 403:
    #                 github_response, i = deal_with_api_403(github_response, i, github_url)
    #             else:
    #                 break
    #
    #     if workflow_url:
    #         workflow_response = request_to_api(workflow_url, i)
    #         while True:
    #             if workflow_response.status_code == 200:
    #                 workflow_json = workflow_response.json()
    #                 for element in workflow_json["tree"]:
    #                     if ".yml" in element["path"]:
    #                         yml_files[f"{owner}/{repository}/{action}"] = element["url"]
    #                         actions += 1
    #                 break
    #             if workflow_response.status_code == 403:
    #                 workflow_response, i = deal_with_api_403(workflow_response, i, workflow_url)
    #             else:
    #                 break
    #
    #     actions_in_repos[action] = actions
    #
    # p_results[index] = (actions_in_repos, yml_files)


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

    for action in loaded_data:
        number_of_open_issues = loaded_data[action]["issues"]["open"]
        number_of_closed_issues = loaded_data[action]["issues"]["closed"]

        open_ones.append(number_of_open_issues)
        closed_ones.append(number_of_closed_issues)

        if number_of_open_issues > 0 and number_of_closed_issues == 0:
            open_no_close_issues += 1
        elif number_of_closed_issues > 0 and number_of_open_issues == 0:
            closed_no_open_issues += 1
        elif number_of_open_issues == 0 and number_of_closed_issues == 0:
            no_issues += 1

        if number_of_open_issues > 0:
            open_issues += 1
            dates = list(loaded_data[action]["versions"])
            dates = [datetime.strptime(date, "%d/%m/%Y") for date in dates]
            dates.sort()
            sorted_dates = [datetime.strftime(date, "%d/%m/%Y") for date in dates]
            last_date = sorted_dates[-1]
            now = datetime.strftime(datetime.now(), "%d/%m/%Y")
            difference = datetime.strptime(now, "%d/%m/%Y") - datetime.strptime(last_date, "%d/%m/%Y")
            days_since_update = difference.days
            if days_since_update > 182:
                open_not_up_to_date += 1
            else:
                open_up_to_date += 1

        if number_of_closed_issues > 0:
            closed_issues += 1

    number_of_actions = len(loaded_data)

    print(f"Mean of open issues for actions: {round(statistics.mean(open_ones), 2)}.")
    print(f"Mean of open issues for actions: {round(statistics.mean(closed_ones), 2)}.\n")

    print(f"Actions with open issues: {open_issues}/{number_of_actions}.\n"
          f"Actions with closed issues: {closed_issues}/{number_of_actions}.\n"
          f"Actions without issues: {no_issues}/{number_of_actions}.\n"
          f"Actions with no issues but open ones: {open_no_close_issues}/{number_of_actions}.\n"
          f"Actions with no issues but closed ones: {closed_no_open_issues}/{number_of_actions}.\n")
    print(f"Actions with the newest open issue that is more than 182 days old: {open_not_up_to_date}.\n"
          f"Actions with the newest open issue that is less than 182 days old: {open_up_to_date}.")


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
    most_common_with_bots = contributors_counter.most_common(sample_size)

    contributors_to_delete = [contributor for contributor in contributors
                              if "-bot" in contributor or "[bot]" in contributor]
    for contributor in contributors_to_delete:
        del contributors[contributor]

    contributors_counter = Counter(contributors)
    most_common_without_bots = contributors_counter.most_common(sample_size)

    return most_common_with_bots, most_common_without_bots


def compare_number_actions_officials_not_officials() -> None:
    """
    Check the number of actions developed by official and not officials users.
    """
    popular_actions_ = actions_popularity()
    popular_actions = {}
    for action in popular_actions_:
        name = action.split("/")[2]
        popular_actions[name] = loaded_data[name]

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
    popular_actions = actions_popularity()

    popular_actions = actions_popularity()
    actions_sample = get_actions_sample()

    try:
        with open("outputs/yml_files.json", 'r', encoding='utf-8') as json_file:
            yml_files = json.load(json_file)
    except FileNotFoundError:
        multiple_results = multiple_actions_start_threads()
        yml_files = multiple_results[1]

    trigger = {}

    i = 0
    for action in popular_actions:
        try:
            api_url = yml_files[action]
        except KeyError:
            continue
        api_response = request_to_api(api_url, i)
        no_content = False
        action_content_encoded = ""

        while True:
            if api_response.status_code == 200:
                api_json = api_response.json()
                action_content_encoded = api_json["content"]
                break
            if api_response.status_code == 403:
                api_response, i = deal_with_api_403(api_response, i, api_url)
            else:
                no_content = True
                break

        if no_content:
            continue

        action_content_decoded = base64.b64decode(action_content_encoded).decode("utf-8").replace("on:", "trigger:")
        action_content_decoded = action_content_decoded.replace('"on":', "trigger:")
        yaml_content = yaml.safe_load(action_content_decoded)
        try:
            triggered_by = yaml_content["trigger"]
        except KeyError:
            continue
        except TypeError:
            continue
        if isinstance(triggered_by, str):
            if triggered_by not in trigger:
                trigger[triggered_by] = 1
            elif triggered_by in trigger:
                trigger[triggered_by] += 1
        else:
            for element in triggered_by:
                if element not in trigger:
                    trigger[element] = 1
                elif element in trigger:
                    trigger[element] += 1

    total_triggers = 0
    for element in trigger:
        total_triggers += trigger[element]

    for element in trigger:
        print(f"{element}: {int(round(trigger[element] / total_triggers, 2) * 100)}%")


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

    popular_versions = [len(loaded_data[action.split("/")[2]]["versions"]) for action in popular_actions]
    actions_versions = [len(loaded_data[action]["versions"]) for action in loaded_data]

    mean_popular_versions = round(statistics.mean(popular_versions), 2)
    mean_not_popular_versions = round(statistics.mean(not_popular_versions), 2)
    mean_versions = round(statistics.mean(actions_versions), 2)
    print(f"Mean for popular actions: {mean_popular_versions}")
    print(f"Mean for not popular actions: {mean_not_popular_versions}")
    print(f"Mean for actions: {mean_versions}")


def compare_number_of_contributors() -> None:
    """
    Compare the number of contributors.
    """
    popular_actions = actions_popularity()

    popular_actions_contributors = [len(loaded_data[action.split("/")[2]]["contributors"])
                                    for action in popular_actions]
    not_popular_actions_contributors = []

    for i in range(samples_to_make):
        not_popular_actions = get_actions_sample(True)
        not_popular_actions_contributors_temp = [len(not_popular_actions[action]["contributors"])
                                                 for action in not_popular_actions]
        not_popular_actions_contributors += not_popular_actions_contributors_temp

    actions_contributors = [len(loaded_data[action]["contributors"]) for action in loaded_data]

    mean_contributors_popular = round(statistics.mean(popular_actions_contributors), 2)
    mean_contributors_not_popular = round(statistics.mean(not_popular_actions_contributors), 2)
    mean_actions = round(statistics.mean(actions_contributors), 2)

    print(f'Popular actions have a mean of {mean_contributors_popular} contributors.')
    print(f'Not popular actions have a mean of {mean_contributors_not_popular} contributors.')
    print(f'Actions have a mean of {mean_actions} contributors.')


def do_actions_use_dependabot() -> None:
    """
    Show the number of actions that use dependabot.
    """
    popular_actions = actions_popularity()
    popular_use_dependabot = 0

    for action in popular_actions:
        action_name = action.split("/")[2]
        contributors = loaded_data[action_name]["contributors"]
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

    # TODO delete
    file = 'outputs/actions_data_17_05_2022.json'
    count = 0
    with open(file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    new = {}
    for element in loaded_data:
        if loaded_data[element]["category"] == 'api-management':
            new[element] = loaded_data[element]
    loaded_data = new
    print(len(loaded_data))
    exit()

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

    if config.actions_popularity:
        actions_popularity(True)

    if config.multiple_actions:
        if config.debug_multiple_actions:
            loaded_data = get_actions_sample(False)
        multiple_actions_start_threads()

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
