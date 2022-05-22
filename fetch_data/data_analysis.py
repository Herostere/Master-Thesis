"""
This script is used to generate plots in order to analyse the data previously retrieved.
"""
from collections import Counter
from datetime import datetime
from fetch_data.fetch_data import (
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

    :param p_category: A string representing the category to plot.
    """
    old_files = config.old_files_names
    actions_data = []
    try:
        for temp_file in old_files:
            with open(temp_file, 'r', encoding='utf-8') as temporary:
                actions_data.append(json.load(temporary))
    except FileNotFoundError:
        print("File not found. Please, check if the file is located in the same folder as this script.")

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
                   "Number of Actions For the Categories")


def actions_technical_lag() -> None:
    """
    Determine the mean for the technical lag of the Actions.
    """
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


def determine_actions_popularity() -> dict:
    """
    Determine the popularity of an Action.
    The popularity is computed as number of stars + number of dependents + number of forks + number of watching.

    :return: The list of most popular Actions for a representative sample.
    """
    scores = {}
    for action in loaded_data.keys():
        stars = loaded_data[action]["stars"]
        dependents = loaded_data[action]["dependents"]["number"]
        forks = loaded_data[action]["forks"]
        watching = loaded_data[action]["watching"]
        score = stars + dependents + forks + watching

        owner = loaded_data[action]["owner"]
        repository = loaded_data[action]["repository"]

        scores[f"{owner}/{repository}/{action}"] = score

    scores_counter = Counter(scores)

    sample_size = compute_sample_size(len(scores))

    popular_actions = scores_counter.most_common(sample_size)

    # for key, value in popular_actions:
    #     key_category = loaded_data[key]["category"]
    #     print(f"{key}: {value} --- {key_category}")

    popular_actions_dictionary = {}
    for couple in popular_actions:
        key = couple[0]
        value = couple[1]
        popular_actions_dictionary[key] = value

    # print(popular_actions_dictionary)
    # print(f"The {sample_size} most popular actions has been writen in the 'popular_actions.json' file.")

    with open('outputs/popular_actions.json', 'w', encoding='utf-8') as json_file:
        json.dump(popular_actions_dictionary, json_file, indent=4)

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
    Check the number of actions per repository. Safe the links to yml files on a JSON.

    :param p_elements: The dictionary with the Actions in it.
    :param p_results: The list in which the data must be saved.
    :param index: The position in the list where the data must be saved.
    """
    actions_in_repos = {}
    yml_files = {}

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
        no_tree = False
        while True:
            if tree_response.status_code == 200:
                tree_json = tree_response.json()
                tree_sha = tree_json["commit"]["tree"]["sha"]
                break
            if tree_response.status_code == 403:
                tree_response, i = deal_with_api_403(tree_response, i, api_branch_url)
            else:
                no_tree = True
                tree_sha = ""
                break

        if no_tree:
            continue

        api_files_main_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{tree_sha}"
        files_response = request_to_api(api_files_main_url, i)
        github_url = ""
        while True:
            if files_response.status_code == 200:
                files_json = files_response.json()
                files = files_json["tree"]
                for element in files:
                    if ".yml" in element["path"]:
                        yml_files[f"{owner}/{repository}/{action}"] = element["url"]
                        actions += 1
                    elif ".github" == element["path"]:
                        github_sha = element["sha"]
                        github_url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{github_sha}"
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
                    for element in github_json["tree"]:
                        if element["path"] == "workflows":
                            workflow_url = element["url"]
                        if ".yml" in element["path"]:
                            yml_files[f"{owner}/{repository}/{action}"] = element["url"]
                            actions += 1
                    break
                if github_response.status_code == 403:
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
                            yml_files[f"{owner}/{repository}/{action}"] = element["url"]
                            actions += 1
                    break
                if workflow_response.status_code == 403:
                    workflow_response, i = deal_with_api_403(workflow_response, i, workflow_url)
                else:
                    break

        actions_in_repos[action] = actions

    p_results[index] = (actions_in_repos, yml_files)


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


def check_issues() -> None:
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

    for action in loaded_data:
        number_of_open_issues = loaded_data[action]["issues"]["open"]
        number_of_closed_issues = loaded_data[action]["issues"]["closed"]

        if number_of_open_issues > 0 and number_of_closed_issues == 0:
            open_no_close_issues += 1
        elif number_of_closed_issues > 0 and number_of_open_issues == 0:
            closed_no_open_issues += 1
        if number_of_open_issues > 0:
            open_issues += 1

            # dates = [key for key in loaded_data[action]["versions"]]
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
        if number_of_open_issues == 0 and number_of_closed_issues == 0:
            no_issues += 1

    no_issues = abs(open_issues - closed_issues)

    print(f"Actions with open issues: {open_issues}.\n"
          f"Actions with closed issues: {closed_issues}.\n"
          f"Action without issues: {no_issues}\n")
    print(f"Actions with the oldest open issue that is more than 182 days old: {open_not_up_to_date}.\n"
          f"Actions with the oldest open issue that is less than 182 days old: {open_up_to_date}.")


def check_contributors_activity() -> tuple[list, list]:
    """
    Retrieve the most active contributors.

    :return: A tuple with the list of most common contributor with bots, and without bots.
    """
    contributors = {}
    for action in loaded_data.keys():
        action_contributors = loaded_data[action]["contributors"]
        for contributor in action_contributors:
            if contributor not in contributors:
                contributors[contributor] = 1
            else:
                contributors[contributor] += 1

    contributors_counter = Counter(contributors)

    sample_size = compute_sample_size(len(contributors))

    # most_active_with_bots = heapq.nlargest(20, contributors.items(), key=lambda i: i[1])
    most_common_with_bots = contributors_counter.most_common(sample_size)

    contributors_to_delete = [contributor for contributor in contributors
                              if "-bot" in contributor or "[bot]" in contributor]
    for contributor in contributors_to_delete:
        del contributors[contributor]

    contributors_counter = Counter(contributors)

    sample_size = compute_sample_size(len(contributors))

    # most_active_without_bots = heapq.nlargest(20, contributors.items(), key=lambda i: i[1])
    most_common_without_bots = contributors_counter.most_common(sample_size)

    return most_common_with_bots, most_common_without_bots


def is_actions_developed_by_officials() -> None:
    """
    Take a sample of all actions and check if the actions are developed by official users.
    """
    sample = {}
    total_number_actions = len(loaded_data)
    sample_size = compute_sample_size(total_number_actions)
    probability = round(sample_size / total_number_actions, 16)
    total_number_sample = len(sample)
    while total_number_sample < sample_size:
        for action in loaded_data:
            random_number = random.random()
            if random_number < probability and action not in sample:
                sample[action] = loaded_data[action]
                total_number_sample = len(sample)
                if total_number_sample == sample_size:
                    break

    official_or_not = {
        "official": 0,
        "unofficial": 0,
    }

    for action in sample:
        if not sample[action]["verified"]:
            official_or_not["official"] += 1
        else:
            official_or_not["unofficial"] += 1

    print(official_or_not)


def how_popular_actions_triggered() -> None:
    """
    Check how the popular actions are triggered on a general basis. Take a representative sample of the most popular
    actions.
    """

    # Representative sample of popular actions
    try:
        with open("outputs/popular_actions.json", 'r', encoding='utf-8') as json_file:
            popular_actions = json.load(json_file)
    except FileNotFoundError:
        popular_actions = determine_actions_popularity()

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
    popular_actions = determine_actions_popularity()
    total_number_actions = len(loaded_data)
    sample_size = compute_sample_size(total_number_actions)

    not_popular_actions = {}
    probability = round(sample_size / total_number_actions, 16)
    total_number_not_popular_actions = len(not_popular_actions)
    while total_number_not_popular_actions < sample_size:
        for action in loaded_data:
            random_number = random.random()
            if random_number < probability and action not in popular_actions:
                versions = loaded_data[action]["versions"]
                not_popular_actions[action] = versions
                total_number_not_popular_actions = len(not_popular_actions)
                if total_number_not_popular_actions == sample_size:
                    break

    popular_versions = []
    for popular_action in popular_actions:
        name = popular_action.split("/")[2]
        for action in loaded_data:
            if name == action:
                versions = len(loaded_data[name]["versions"])
                popular_versions.append(versions)
                break
    not_popular_versions = [len(not_popular_actions[action]) for action in not_popular_actions]

    mean_popular_versions = round(statistics.mean(popular_versions), 2)
    mean_not_popular_versions = round(statistics.mean(not_popular_versions), 2)
    print(f"Mean for popular actions: {mean_popular_versions}")
    print(f"Mean for not popular actions: {mean_not_popular_versions}")


def compare_contributors_popular_not_popular() -> None:
    """
    Compare the number of contributors for popular and not popular actions.
    Take a sample of both popular and not popular actions,
    """
    popular_actions = determine_actions_popularity()

    total_number_actions = len(loaded_data)
    sample_size = compute_sample_size(total_number_actions)
    not_popular_actions = {}
    probability = round(sample_size / total_number_actions, 16)
    total_number_not_popular_actions = len(not_popular_actions)
    while total_number_not_popular_actions < sample_size:
        for action in loaded_data:
            random_number = random.random()
            if random_number < probability and action not in popular_actions:
                not_popular_actions[action] = loaded_data[action]
                total_number_not_popular_actions = len(not_popular_actions)
                if total_number_not_popular_actions == sample_size:
                    break

    popular_actions_contributors = [len(loaded_data[action.split("/")[2]]["contributors"])
                                    for action in popular_actions]
    not_popular_actions_contributors = [len(not_popular_actions[action]["contributors"])
                                        for action in not_popular_actions]

    print(round(statistics.mean(popular_actions_contributors), 2))
    print(round(statistics.mean(not_popular_actions_contributors), 2))


def do_actions_use_dependabot() -> None:
    """
    Show the number of actions that use dependabot.
    """
    popular_actions = determine_actions_popularity()
    popular_use_dependabot = 0

    for action in popular_actions:
        action_name = action.split("/")[2]
        contributors = loaded_data[action_name]["contributors"]
        if "dependabot[bot]" in contributors:
            popular_use_dependabot += 1

    total_number_actions = len(loaded_data)
    sample_size = compute_sample_size(total_number_actions)

    not_popular_actions = {}
    probability = round(sample_size / total_number_actions, 16)
    total_number_not_popular_actions = len(not_popular_actions)
    while total_number_not_popular_actions < sample_size:
        for action in loaded_data:
            random_number = random.random()
            if random_number < probability and action not in popular_actions:
                not_popular_actions[action] = loaded_data[action]
                total_number_not_popular_actions = len(not_popular_actions)
                if total_number_not_popular_actions == sample_size:
                    break

    not_popular_use_dependabot = 0
    for action in not_popular_actions:
        contributors = loaded_data[action]["contributors"]
        if "dependabot[bot]" in contributors:
            not_popular_use_dependabot += 1

    total_popular_actions = len(popular_actions)
    print(f"{popular_use_dependabot}/{total_popular_actions} popular actions are using dependabot.")
    print(f"{not_popular_use_dependabot}/{sample_size} not popular actions are using dependabot.")


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
        determine_actions_popularity()

    if config.multiple_actions:
        if config.debug_multiple_actions:
            new_data = {}
            data_keys = loaded_data.keys()
            data_in_new = 0
            for key_1 in data_keys:
                if data_in_new < 20:
                    new_data[key_1] = loaded_data[key_1]
                    data_in_new += 1
                else:
                    break
            loaded_data = new_data
        multiple_actions_start_threads()

    if config.actions_issues:
        check_issues()

    if config.contributors_activity:
        check_contributors_activity()

    if config.is_actions_developed_by_officials:
        is_actions_developed_by_officials()

    if config.how_popular_actions_triggered:
        how_popular_actions_triggered()

    if config.compare_number_of_versions:
        compare_number_of_versions()

    if config.compare_contributors_popular_not_popular:
        compare_contributors_popular_not_popular()

    if config.do_actions_use_dependabot:
        do_actions_use_dependabot()
