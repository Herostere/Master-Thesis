"""
This script is used to analyse the data about GitHub Actions.
"""
from datetime import datetime
from fetch_data import request_to_api
from packaging import version as packaging_version
from scipy.stats import mannwhitneyu, ttest_ind

import data_analysis_config as config
import matplotlib.pyplot as plt
import numpy
import packaging.version
import os
import re
import seaborn
import sqlite3
import statistics
import threading
import yaml
import yaml.constructor
import yaml.parser
import yaml.scanner


def rq1() -> None:
    """
    Observe the number of Actions on the Marketplace.
    """
    first_observation = True
    second_observation = True
    third_observation = True

    if first_observation:
        dates, number_of_actions, lists_of_actions = get_number_of_actions_all_files()
        print(f"Overall number of Actions on the different dates: {number_of_actions}")
        seaborn.scatterplot(x=dates, y=number_of_actions)
        seaborn.lineplot(x=dates, y=number_of_actions)
        plt.show()

        actions_added_list = []
        actions_deleted_list = []

        for i in range(len(lists_of_actions)-1):
            j = i + 1
            new_actions = 0
            actions_lost = 0
            first_list = lists_of_actions[i]
            second_list = lists_of_actions[j]
            for action in second_list:
                if action not in first_list:
                    new_actions += 1
            for action in first_list:
                if action not in second_list:
                    actions_lost += 1
            actions_added_list.append(new_actions)
            actions_deleted_list.append(actions_lost)
            print(f"Between {dates[i]} and {dates[j]}: {new_actions} Actions added.")
            print(f"Between {dates[i]} and {dates[j]}: {actions_lost} Actions removed.")
            print("**" * 5)
            i += 1

        seaborn.scatterplot(x=dates[1:], y=actions_added_list, color='mediumseagreen')
        seaborn.lineplot(x=dates[1:], y=actions_added_list, color='mediumseagreen', label="Actions added")
        seaborn.scatterplot(x=dates[1:], y=actions_deleted_list, color='darkorange')
        seaborn.lineplot(x=dates[1:], y=actions_deleted_list, color='darkorange', label="Actions removed")
        plt.show()

    if second_observation:
        dates, number_of_actions = get_number_of_actions_categories()
        for i in range(len(categories_main)):
            print(categories_main[i])
            category_values = [values[i] for values in number_of_actions]
            print(category_values)
            seaborn.scatterplot(x=dates, y=category_values)
            seaborn.lineplot(x=dates, y=category_values)
            plt.show()
            print("-" * 10)

    if third_observation:
        dates, list_categories_added, list_categories_deleted = get_actions_in_category()
        overall_added = {}
        overall_deleted = {}
        for dict_added in list_categories_added:
            for category in dict_added:
                if category not in overall_added:
                    overall_added[category] = dict_added[category]
                else:
                    overall_added[category] += dict_added[category]
        for dict_deleted in list_categories_deleted:
            for category in dict_deleted:
                if category not in overall_deleted:
                    overall_deleted[category] = dict_deleted[category]
                else:
                    overall_deleted[category] += dict_deleted[category]
        print(f"Times added: {overall_added}")
        print(f"Time deleted: {overall_deleted}")


def get_number_of_actions_all_files() -> tuple[list, list, list]:
    """
    Get the number of Actions for the different dates, and the list of Actions.

    :return: The different dates in a list, the number of Actions in a list, and the list of Actions
    """
    dates = []
    number_of_actions = []
    lists_of_actions = []

    for file in files_names_main:
        sqlite_connection = sqlite3.connect(f"{files_path_main}/{file}")
        sqlite_cursor = sqlite_connection.cursor()

        dates.append(file.split("actions_data_")[1].split(".db")[0].replace("_", "/"))

        number_of_actions_query = """
        SELECT COUNT(*) FROM actions;
        """
        local_number_of_actions = sqlite_cursor.execute(number_of_actions_query).fetchone()[0]
        number_of_actions.append(local_number_of_actions)

        local_list_of_actions = get_all_actions_names(sqlite_cursor)
        lists_of_actions.append(local_list_of_actions)

        sqlite_connection.close()

    return dates, number_of_actions, lists_of_actions


def get_actions_in_category() -> tuple[list[tuple[str, str]], list[dict], list[dict]]:
    """
    Get the added/deleted categories for the different files.

    :return: The dates, the list of added categories, and the list of deleted categories.
    """
    dates = []

    list_categories_added = []
    list_categories_deleted = []

    for i in range(len(files_names_main) - 1):
        j = i + 1

        categories_added = {}
        categories_deleted = {}

        date_1 = files_names_main[i].split("actions_data_")[1].split(".db")[0].replace("_", "/")
        date_2 = files_names_main[j].split("actions_data_")[1].split(".db")[0].replace("_", "/")
        dates.append((date_1, date_2))

        sqlite_connection_1 = sqlite3.connect(f"{files_path_main}/{files_names_main[i]}")
        sqlite_cursor_1 = sqlite_connection_1.cursor()
        sqlite_connection_2 = sqlite3.connect(f"{files_path_main}/{files_names_main[j]}")
        sqlite_cursor_2 = sqlite_connection_2.cursor()

        list_of_actions_1 = get_all_actions_names(sqlite_cursor_1)
        list_of_actions_2 = get_all_actions_names(sqlite_cursor_2)

        for action in list_of_actions_2:
            if action in list_of_actions_1:
                categories_1 = get_categories_of_action(sqlite_cursor_1, action)
                categories_2 = get_categories_of_action(sqlite_cursor_2, action)

                for category in categories_2:
                    if category not in categories_1:
                        if category not in categories_added:
                            categories_added[category] = 1
                        else:
                            categories_added[category] += 1

                for category in categories_1:
                    if category not in categories_2:
                        if category not in categories_deleted:
                            categories_deleted[category] = 1
                        else:
                            categories_deleted[category] += 1

        sqlite_connection_1.close()
        sqlite_connection_2.close()

        list_categories_added.append(categories_added)
        list_categories_deleted.append(categories_deleted)

    return dates, list_categories_added, list_categories_deleted


def get_number_of_actions_categories() -> tuple[list, list]:
    """
    Get the number of Actions for all categories on different dates.

    :return: A list of dates, and a list of lists containing the values.
    """
    dates = []
    values = []

    for file in files_names_main:
        sqlite_connection = sqlite3.connect(f"{files_path_main}/{file}")
        sqlite_cursor = sqlite_connection.cursor()

        dates.append(file.split("actions_data_")[1].split(".db")[0].replace("_", "/"))

        values_categories = []
        for category in categories_main:

            number_of_actions_query = """
            SELECT COUNT(*) FROM categories WHERE category=?;
            """
            local_number_of_actions = sqlite_cursor.execute(number_of_actions_query, (category,)).fetchone()[0]
            values_categories.append(local_number_of_actions)

        values.append(values_categories)
        sqlite_connection.close()

    return dates, values


def rq2() -> None:
    """
    Observe the categories of Actions that are the most commonly proposed on the Marketplace.
    """
    first_observation = True
    second_observation = True

    actions_per_categories = number_of_actions_per_categories()
    categories_to_display = list(actions_per_categories.keys())
    actions_to_display = list(actions_per_categories.values())

    compute_statistics(actions_to_display, "of actions per categories")

    if first_observation:
        bar_plot = seaborn.barplot(x=categories_to_display, y=actions_to_display, orient="v", color="steelblue")
        bar_plot.bar_label(bar_plot.containers[0])
        plt.xticks(rotation=90)
        plt.show()

    if second_observation:
        seaborn.boxplot(y=actions_to_display)
        plt.show()


def number_of_actions_per_categories() -> dict:
    """
    Get the number of actions for each categories in the first file. Short them from higher to lowest.

    :return: Dictionary with the name of the category as key and the number of Actions as value.
    """
    _, actions_per_categories = get_number_of_actions_categories()
    to_sort_by_keys = {}
    for i in range(len(categories_main)):
        to_sort_by_keys[categories_main[i]] = actions_per_categories[-1][i]
    sorted_by_keys = {k: to_sort_by_keys[k] for k in sorted(to_sort_by_keys, key=to_sort_by_keys.get, reverse=True)}
    return sorted_by_keys


def rq3() -> None:
    perform_t_test = True
    perform_mann_whitney_u_test = True
    compute_lag_statistics = True
    show_general_information = True
    show_plots = True

    fetch_repositories_query = """
        SELECT DISTINCT owner, repository FROM versions;
        """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()
    owners_repositories = sqlite_cursor.execute(fetch_repositories_query).fetchall()

    overall_major_updates_lag = []
    overall_minor_updates_lag = []
    overall_patch_updates_lag = []
    overall_updates_lag = []

    overall_number_of_versions = 0

    legacy = 0
    refused = 0
    inconsistencies = 0

    for owner, repository in owners_repositories:
        fetch_date_and_versions_query = """
            SELECT date, version FROM versions WHERE owner=? AND repository=?;
            """
        dates_and_versions = sqlite_cursor.execute(fetch_date_and_versions_query, (owner, repository)).fetchall()
        dates_and_versions.sort(key=lambda tup: tup[0])
        major_updates_lag = []
        minor_updates_lag = []
        patch_updates_lag = []

        overall_number_of_versions += len(dates_and_versions)

        run = False
        i = 0
        previous_date = None
        previous_major = None
        previous_minor = None
        previous_patch = None
        previous_major_date = None
        previous_minor_date = None
        previous_patch_date = None
        while i < len(dates_and_versions):
            try:
                previous_date = datetime.strptime(dates_and_versions[i][0], "%Y-%m-%d %H:%M:%S")
                previous_major_date = previous_date
                previous_minor_date = previous_date
                previous_patch_date = previous_date
                not_ready_version = str(dates_and_versions[i][1])
                previous_version = packaging_version.parse(not_ready_version)

                test_previous = re.search(r"\d+(\.\d+){0,2}", str(previous_version))

                if type(previous_version) is packaging.version.LegacyVersion and test_previous:
                    legacy += 1
                    test_previous = test_previous.span()
                    previous_version_string = str(previous_version)[test_previous[0]:test_previous[1]]
                    previous_version = packaging_version.parse(previous_version_string)
                elif type(previous_version) is packaging.version.LegacyVersion:
                    refused += 1

                previous_major = previous_version.major
                previous_minor = previous_version.minor
                previous_patch = previous_version.micro

                run = True
                break
            except AttributeError:
                refused += 1
                i += 1

        if run:
            for date_version in dates_and_versions[i + 1:]:
                current_date = datetime.strptime(date_version[0], "%Y-%m-%d %H:%M:%S")

                difference_for_overall = current_date - previous_date
                elapsed_seconds_for_overall = difference_for_overall.seconds
                elapsed_days_for_overall = difference_for_overall.days
                days_seconds_for_overall = elapsed_days_for_overall * 24 * 60 * 60
                overall_updates_lag.append(elapsed_seconds_for_overall + days_seconds_for_overall)

                current_version = packaging_version.parse(str(date_version[1]))

                test_current = re.search(r"\d+(\.\d+){0,2}", str(current_version))

                if type(current_version) is packaging.version.LegacyVersion and test_current:
                    legacy += 1
                    test_current = test_current.span()
                    current_version_sting = str(current_version)[test_current[0]:test_current[1]]
                    current_version = packaging_version.parse(current_version_sting)
                elif type(current_version) is packaging.version.LegacyVersion:
                    refused += 1

                try:
                    current_major = current_version.major
                    current_minor = current_version.minor
                    current_patch = current_version.micro
                except AttributeError:
                    continue

                if current_major > previous_major:
                    difference = current_date - previous_major_date
                    elapsed_seconds = difference.seconds
                    elapsed_days = difference.days
                    days_seconds = elapsed_days * 24 * 60 * 60
                    major_updates_lag.append(elapsed_seconds + days_seconds)
                    previous_major_date = current_date
                    previous_major = current_major
                    previous_minor = current_minor
                    previous_patch = current_patch
                elif current_major == previous_major and current_minor > previous_minor:
                    difference = current_date - previous_minor_date
                    elapsed_seconds = difference.seconds
                    elapsed_days = difference.days
                    days_seconds = elapsed_days * 24 * 60 * 60
                    minor_updates_lag.append(elapsed_seconds + days_seconds)
                    previous_minor_date = current_date
                    previous_minor = current_minor
                    previous_patch = current_patch
                elif current_major == previous_major and current_minor == previous_minor and current_patch > previous_patch:
                    difference = current_date - previous_patch_date
                    elapsed_seconds = difference.seconds
                    elapsed_days = difference.days
                    days_seconds = elapsed_days * 24 * 60 * 60
                    patch_updates_lag.append(elapsed_seconds + days_seconds)
                    previous_patch_date = current_date
                    previous_patch = current_patch
                else:
                    inconsistencies += 1
                    previous_major = current_major
                    previous_minor = current_minor
                    previous_patch = current_patch

            for element in major_updates_lag:
                overall_major_updates_lag.append(element)
            for element in minor_updates_lag:
                overall_minor_updates_lag.append(element)
            for element in patch_updates_lag:
                overall_patch_updates_lag.append(element)

    sqlite_connection.close()

    if perform_t_test:
        print(ttest_ind(a=overall_major_updates_lag, b=overall_minor_updates_lag))
        print(ttest_ind(a=overall_major_updates_lag, b=overall_patch_updates_lag))
        print(ttest_ind(a=overall_minor_updates_lag, b=overall_patch_updates_lag))
        print('-' * 20)

    if perform_mann_whitney_u_test:
        print(mannwhitneyu(overall_major_updates_lag, overall_minor_updates_lag))
        print(mannwhitneyu(overall_major_updates_lag, overall_patch_updates_lag))
        print(mannwhitneyu(overall_minor_updates_lag, overall_patch_updates_lag))
        print('-' * 20)

    if compute_lag_statistics:
        compute_statistics(overall_major_updates_lag, "for major releases.")
        print('x' * 10)
        compute_statistics(overall_minor_updates_lag, "for minor releases.")
        print('x' * 10)
        compute_statistics(overall_patch_updates_lag, "for patch releases.")
        print('x' * 10)
        compute_statistics(overall_updates_lag, "for all releases.")
        print('-' * 20)

    if show_general_information:
        print(f"Overall number of versions: {overall_number_of_versions}")
        print(f"Number of legacy converted to pep440: {legacy}")
        print(f"Number of refused: {refused}")
        print(f"Number of inconsistencies: {inconsistencies}")
        print(f"Number of detected major updates: {len(overall_major_updates_lag)}")
        print(f"Number of detected minor updates: {len(overall_minor_updates_lag)}")
        print(f"Number of detected patch updates: {len(overall_patch_updates_lag)}")
        print('-' * 20)

    if show_plots:
        fig, axs = plt.subplots(ncols=3)
        plot_major = seaborn.boxplot(y=overall_major_updates_lag, ax=axs[0])
        plot_minor = seaborn.boxplot(y=overall_minor_updates_lag, ax=axs[1], color='MediumSeaGreen')
        plot_patch = seaborn.boxplot(y=overall_patch_updates_lag, ax=axs[2], color='Brown')
        plot_major.set(title="Major releases")
        plot_minor.set(title="Minor releases")
        plot_patch.set(title="Path releases")
        plot_major.set(yscale='log')
        plot_minor.set(yscale='log')
        plot_patch.set(yscale='log')
        plt.show()
        plot_any = seaborn.boxplot(y=overall_updates_lag)
        plot_any.set(yscale='log')
        plt.show()


def convert_seconds(seconds: float) -> str:
    """
    Convert the number of seconds to days, hours, minutes, and seconds.

    :param seconds: The number of seconds.
    :return: A string indicating the number of days, hours, minutes, and seconds.
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    sentence = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
    return sentence


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


def rq4() -> None:
    """
    Determine the number of Actions used by workflow files.
    """
    number_of_repositories = config.rq4_number_of_repositories

    already_fetch_yml_files = os.path.exists(f"outputs/yml_files_{number_of_repositories}.npy")
    if not already_fetch_yml_files:
        list_of_workflow_files_contents = get_workflow_files(number_of_repositories)
        numpy.save(f"outputs/yml_files_{number_of_repositories}.npy", list_of_workflow_files_contents)
    list_of_workflow_files_contents = numpy.load(f"outputs/yml_files_{number_of_repositories}.npy")
    ignore_checkout = config.rq4_ignore_checkout
    total_of_actions, total_of_distinct_actions, actions_counters, no_actions, checkouts = actions_per_workflow_file(
        list_of_workflow_files_contents, ignore_checkout)
    actions_counters = sorted(actions_counters.items(), key=lambda x: x[1], reverse=True)
    actions_counters = dict(actions_counters)

    compute_statistics(total_of_actions, "of Actions per workflow file")
    print('-' * 10)
    compute_statistics(total_of_distinct_actions, "of distinct Actions per workflow file")
    print('-' * 10)
    print(actions_counters)
    print('-' * 10)
    print(f"Overall distinct Actions: {len(actions_counters)}")
    print('-' * 10)
    print(f"Not using Actions available on marketplace: {no_actions}")
    print('-' * 10)
    print(f"Workflow files using checkout: {checkouts}")
    fig, axs = plt.subplots(ncols=2)
    plot_total = seaborn.boxplot(y=total_of_actions, ax=axs[0])
    plot_distinct_total = seaborn.boxplot(y=total_of_distinct_actions, ax=axs[1], color='MediumSeaGreen')
    plot_total.set(title="# of Actions")
    plot_distinct_total.set(title="# of distinct Actions")
    plt.show()
    actions_uses = [actions_counters[action] for action in actions_counters]
    compute_statistics(actions_uses, "of uses for Actions")
    p_25, p_75 = numpy.percentile(actions_uses, [25, 75])
    iqr = p_75 - p_25
    upper_bound = p_75 + 1.5 * iqr
    lower_bound = p_25 - 1.5 * iqr
    actions_uses_no_outliers = [number for number in actions_uses if lower_bound <= number <= upper_bound]
    seaborn.boxplot(y=actions_uses_no_outliers)
    plt.show()


def get_workflow_files(number_of_files: int) -> list:
    """
    Get a list of workflow files contents.

    :param number_of_files: The number of files needed.
    :return: List containing the content of workflow files.
    """
    workflow_files_contents = []
    end_cursor = None
    number_of_workflow_files = 0

    while number_of_workflow_files < number_of_files:
        if not end_cursor:
            api_answer_json = get_api("repositories")
        else:
            api_answer_json = get_api("repositories", end_cursor)

        if api_answer_json:
            end_cursor = api_answer_json["pageInfo"]["endCursor"]
            repositories = api_answer_json["edges"]
            repositories_workflow_ymls = filter_repositories_workflow_files(repositories)
            for file in repositories_workflow_ymls:
                workflow_files_contents.append(file)
            number_of_workflow_files = len(workflow_files_contents)
            print("-"*10 + " " + str(number_of_workflow_files))

    return workflow_files_contents[:number_of_files]


def get_api(key_word, repository=None, owner=None, expression=None, end_cursor=None) -> dict | None:
    """
    Contact the API to fetch information.

    :param key_word: The keyword used to determine the query for the API.
    :param repository: The name of the repository.
    :param owner: The owner of the repository.
    :param expression: The expression to use in the query.
    :param end_cursor: The cursor to get the next page in the query.
    :type key_word: str
    :type repository: str
    :type owner: str
    :type expression: str
    :type end_cursor: str
    :return: The JSON with the requested data or None if error in the response.
    """
    if key_word == "repositories" and not end_cursor:
        query = {'query': f"""
    {{
      search(query: "is:public pushed:>=2021-07-20", type: REPOSITORY, first: 100) {{
        repositoryCount
        pageInfo {{
          endCursor
          startCursor
        }}
        edges {{
          node {{
            ... on Repository {{
              url
              owner {{
                login
              }}
              name
              defaultBranchRef {{
                name
              }}
            }}
          }}
        }}
      }}
    }}
    """}
        api_response_keyword = "search"
    elif key_word == "repositories":
        query = {'query': f"""
            {{
              search(query: "is:public pushed:>=2021-07-20", type: REPOSITORY, first: 100, after: "{end_cursor}") {{
                repositoryCount
                pageInfo {{
                  endCursor
                  startCursor
                }}
                edges {{
                  node {{
                    ... on Repository {{
                      url
                      owner {{
                        login
                      }}
                      name
                      defaultBranchRef {{
                        name
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """}
        api_response_keyword = "search"
    elif key_word == "file_content":
        query = {'query': f"""
            {{
              repository(name: "{repository}", owner: "{owner}") {{
                object(expression: "{expression}") {{
                  ... on Blob {{
                    text
                  }}
                }}
              }}
            }}            
            """}
        api_response_keyword = "repository"
    elif key_word == "last_open_issue":
        query = {'query': f"""
            {{
              repository(name: "{repository}", owner: "{owner}") {{
                issues(last: 1, states: OPEN) {{
                  edges {{
                    node {{
                      createdAt
                    }}
                  }}
                }}
              }}
            }}            
            """}
        api_response_keyword = "repository"
    elif key_word == "last_closed_issue":
        query = {'query': f"""
            {{
              repository(name: "{repository}", owner: "{owner}") {{
                issues(last: 1, states: CLOSED) {{
                  edges {{
                    node {{
                      createdAt
                    }}
                  }}
                }}
              }}
            }}            
            """}
        api_response_keyword = "repository"
    else:
        query = {'query': f"""
    {{
      repository(name: "{repository}", owner: "{owner}") {{
        object(expression: "{expression}") {{
          ... on Tree {{
            entries {{
              name
              path
            }}
          }}
        }}
      }}
    }}
    """}
        api_response_keyword = "repository"

    api_response = request_to_api(query)
    api_response_json = api_response.json()["data"][api_response_keyword] if api_response else None

    return api_response_json


def filter_repositories_workflow_files(repositories: list) -> list:
    """
    Get the workflow files from repositories using GitHub Actions.

    :param repositories: A list of repositories.
    :return: A list a workflow files contents.
    """
    number_of_threads = config.rq4_number_of_threads
    number_of_threads = number_of_threads if number_of_threads > 0 else 4
    number_of_threads = number_of_threads if number_of_threads < 11 else 4

    threads = []
    yml_content = []

    lists_of_repositories = numpy.array_split(repositories, number_of_threads)
    for array in lists_of_repositories:
        threads.append(threading.Thread(target=thread_filter_repositories_workflow_files, args=(yml_content, array)))

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return yml_content


def thread_filter_repositories_workflow_files(yml_content: list, repositories: list) -> None:
    """
    Filter repositories and extract the content of workflow files.

    :param yml_content: List with the content of workflow files. Will be populated by threads, should be empty at first.
    :param repositories: The list of repositories that will be analyzed by a thread.
    """
    for node in repositories:
        repository = node["node"]
        owner = repository["owner"]["login"]
        repo_name = repository["name"]
        branch = repository["defaultBranchRef"]["name"]
        expression = f"{branch}:.github/workflows"
        api_response_json = get_api("content_of_repo", repo_name, owner, expression)
        if api_response_json and api_response_json["object"]:
            entries = api_response_json["object"]["entries"]
            for entry in entries:
                path = entry["path"]
                if ".yml" in path or ".yaml" in path:
                    expression = f"{branch}:{path}"
                    json_content = get_api("file_content", owner=owner, repository=repo_name, expression=expression)
                    content = json_content["object"]["text"] if json_content else ""
                    if content:
                        yml_content.append(content)


def actions_per_workflow_file(list_of_workflow_files_contents, ignore_checkout=False):
    """
    Count the number of Actions per workflow files.

    :param list_of_workflow_files_contents: List with the content of workflow files.
    :param ignore_checkout: True if we want to ignore "checkout" in the count of Actions.
    :type list_of_workflow_files_contents: numpy.ndarray
    :type ignore_checkout: bool
    :return: A tuple with the number of Actions per workflow file, the number of distinct Actions per workflow file
    a dictionary with the count of each Action usage, the number of workflow files not using Actions available on the
    Marketplace, and the number of workflow files using the checkout Action.
    :rtype: tuple[list, list, dict, int, int]
    """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()

    list_of_actions_on_marketplace = get_all_actions_names(sqlite_cursor)
    list_of_actions_on_marketplace = [f"{action[0]}/{action[1]}" for action in list_of_actions_on_marketplace]

    sqlite_connection.close()

    total_of_actions = []
    total_of_distinct_actions = []
    actions_counters = {}
    no_actions = 0
    checkouts = 0
    for workflow_content in list_of_workflow_files_contents:
        actions_counter = 0
        distinct_actions = []
        uses_checkout = False
        pre_content = workflow_content.replace("on:", "trigger:").replace("\t", "    ")
        pre_content = re.sub(r"\n+", "\n", pre_content)
        content = yaml.safe_load(pre_content)
        at_least_one_action = False
        if content and "jobs" in content.keys():
            jobs = content["jobs"]
            for job in jobs:
                if "steps" in jobs[job].keys():
                    steps = jobs[job]["steps"]
                    for step in steps:
                        step_keys = step.keys()
                        for key in step_keys:
                            if key == "uses":
                                use = step[key]
                                use = use.split("@")[0] if "@" in use else use
                                checkout = use == "actions/checkout"
                                uses_checkout = True if checkout else uses_checkout
                                should_ignore = checkout and ignore_checkout
                                if use in list_of_actions_on_marketplace and not should_ignore:
                                    at_least_one_action = True
                                    actions_counter += 1
                                    if use not in distinct_actions:
                                        distinct_actions.append(use)
                                    if use not in actions_counters:
                                        actions_counters[use] = 1
                                    else:
                                        actions_counters[use] += 1
        total_of_actions.append(actions_counter)
        total_of_distinct_actions.append(len(distinct_actions))
        no_actions = no_actions + 1 if not at_least_one_action else no_actions
        checkouts = checkouts + 1 if uses_checkout else checkouts
    return total_of_actions, total_of_distinct_actions, actions_counters, no_actions, checkouts


def rq5() -> None:
    """
    Determine the popularity of the Actions.
    """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()

    actions_with_metrics = get_actions_with_metrics(sqlite_cursor)

    top_n = 1000
    most_popular = n_most_popular_actions(actions_with_metrics, top_n, sqlite_cursor)
    sqlite_connection.close()
    print(most_popular)

    sqlite_cursor.close()


def get_actions_with_metrics(sqlite_cursor: sqlite3.Cursor) -> dict:
    """
    Get the Actions with their metrics to answer RQ5.

    :param sqlite_cursor: The cursor for the database connection.
    :return: The dictionary with the metrics for all Actions.
    """
    actions_with_metrics = {}

    names_of_actions = get_all_actions_names(sqlite_cursor)
    for action in names_of_actions:
        stars = get_specific_action_stars(sqlite_cursor, action)
        forks = get_specific_action_forks(sqlite_cursor, action)
        watchers = get_specific_action_watchers(sqlite_cursor, action)
        dependents = get_specific_action_dependents(sqlite_cursor, action)
        contributors = get_specific_action_contributors(sqlite_cursor, action)
        actions_with_metrics[action] = {}
        actions_with_metrics[action]["stars"] = stars
        actions_with_metrics[action]["forks"] = forks
        actions_with_metrics[action]["watchers"] = watchers
        actions_with_metrics[action]["dependents"] = dependents
        actions_with_metrics[action]["contributors"] = contributors

    return actions_with_metrics


def get_all_actions_names(sqlite_cursor: sqlite3.Cursor) -> list:
    """
    Get the names of all Actions within the database.

    :param sqlite_cursor: The cursor for the database connection.
    :return: List containing the owner, repository, and the name of an Action, as tuple.
    """
    get_actions_names_query = """
    SELECT owner, repository, name FROM actions; 
    """
    actions_names = sqlite_cursor.execute(get_actions_names_query).fetchall()
    return actions_names


def get_specific_action_stars(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str]) -> int:
    """
    Get the number of stars for a specific Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name).
    :return: The number of stars for the specific Action.
    """
    get_stars_of_action_query = """
    SELECT stars FROM actions WHERE owner=? AND repository=? AND name=?;
    """
    stars_of_action = sqlite_cursor.execute(get_stars_of_action_query, action).fetchone()[0]
    return stars_of_action


def get_specific_action_forks(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str]) -> int:
    """
    Get the number of forks for a specific Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name).
    :return: The number of forks for the specific Action.
    """
    get_forks_of_action_query = """
    SELECT forks FROM actions WHERE owner=? AND repository=? AND name=?;
    """
    forks_of_action = sqlite_cursor.execute(get_forks_of_action_query, action).fetchone()[0]
    return forks_of_action


def get_specific_action_watchers(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str]) -> int:
    """
    Get the number of watchers for a specific Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name).
    :return: The number of watchers for the specific Action.
    """
    get_watchers_of_action_query = """
    SELECT watchers FROM actions WHERE owner=? AND repository=? AND name=?;
    """
    watchers_of_action = sqlite_cursor.execute(get_watchers_of_action_query, action).fetchone()[0]
    return watchers_of_action


def get_specific_action_dependents(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str]) -> int:
    """
    Get the number of dependents for a specific Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name).
    :return: The number of dependents for the specific Action.
    """
    get_dependents_of_action_query = """
    SELECT number FROM dependents WHERE owner=? AND repository=?;
    """
    dependents_of_action = sqlite_cursor.execute(get_dependents_of_action_query, (action[0], action[1])).fetchone()[0]
    return dependents_of_action


def get_specific_action_contributors(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str]) -> int:
    """
    Get the number of contributors for a specific Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name).
    :return: The number of contributors for the specific Action.
    """
    get_contributors_of_action_query = """
    SELECT COUNT(*) FROM (SELECT owner, repository, contributor FROM contributors WHERE owner=? AND repository=?);
    """
    owner = action[0]
    repo = action[1]
    contributors_of_action = sqlite_cursor.execute(get_contributors_of_action_query, (owner, repo)).fetchone()[0]
    return contributors_of_action


def n_most_popular_actions(actions_with_metrics: dict, n: int, sqlite_cursor: sqlite3.Cursor) -> list:
    """
    Show the list of most popular owners, categories, and Actions.

    :param actions_with_metrics: The dictionary of Actions along with their number of stars, forks, ...
    :param n: The n top Actions to show.
    :param sqlite_cursor: The cursor for the database connection.
    :return: The most popular Actions.
    """
    actions_with_scores = []
    for action in actions_with_metrics:
        stars = actions_with_metrics[action]["stars"]
        forks = actions_with_metrics[action]["forks"]
        watchers = actions_with_metrics[action]["watchers"]
        dependents = actions_with_metrics[action]["dependents"]
        contributors = actions_with_metrics[action]["contributors"]

        score = 25 * stars + 75 * forks + 50 * watchers + 100 * contributors + dependents
        actions_with_scores.append((action, score))

    actions_with_scores.sort(key=lambda x: x[1], reverse=True)
    top_n = actions_with_scores[:n]
    for i in range(len(top_n)):
        action = top_n[i][0]
        score = top_n[i][1]
        categories = get_categories_of_action(sqlite_cursor, action)
        top_n[i] = (action, score, categories)

    categories_counter = {}
    owners_counter = {}
    for action in top_n:
        categories = action[2]
        owner = action[0][0]
        if owner not in owners_counter:
            owners_counter[owner] = 1
        else:
            owners_counter[owner] += 1
        for category in categories:
            if category not in categories_counter:
                categories_counter[category] = 1
            else:
                categories_counter[category] += 1
    owners_counter = sorted(owners_counter.items(), key=lambda x: x[1], reverse=True)
    owners_counter = dict(owners_counter)
    print(owners_counter)
    categories_counter = sorted(categories_counter.items(), key=lambda x: x[1], reverse=True)
    categories_counter = dict(categories_counter)
    one_action = 0
    for owner in owners_counter:
        if owners_counter[owner] == 1:
            one_action += 1
    print(f"Owner with only one Action: {one_action} / {len(owners_counter)}")
    print(categories_counter)
    return top_n


def get_categories_of_action(sqlite_cursor: sqlite3.Cursor, action: tuple[str, str, str] | tuple[str, str]) -> list:
    """
    Get the list of categories (max len = 2) for an Action.

    :param sqlite_cursor: The cursor for the database connection.
    :param action: The specific Action (owner, repository, name) | (owner, repository).
    :return: The categories for an Action.
    """
    get_category_of_action_query = """
    SELECT category FROM categories WHERE owner = ? AND repository = ?;
    """
    owner = action[0]
    repo = action[1]
    categories_tuples = sqlite_cursor.execute(get_category_of_action_query, (owner, repo)).fetchall()
    categories = []
    for category_tuple in categories_tuples:
        categories.append(category_tuple[0])
    return categories


def rq6() -> None:
    """
    Determine the number of issues per Action.
    """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()

    well_maintained_actions, not_well_maintained_actions = number_of_well_not_well_maintained_actions(sqlite_cursor)
    print("-" * 10)
    number_of_issues(sqlite_cursor, well_maintained_actions)
    print("-" * 10)
    number_of_issues(sqlite_cursor, not_well_maintained_actions)
    print("-" * 10)
    number_of_actions_with_issues(sqlite_cursor)
    print("-" * 10)
    number_of_actions_with_open_issues(sqlite_cursor)
    print("-" * 10)
    number_of_actions_with_closed_issues(sqlite_cursor)

    sqlite_connection.close()


def number_of_well_not_well_maintained_actions(sqlite_cursor: sqlite3.Cursor) -> tuple[list, list]:
    """
    Get the number of not well maintained Actions, Actions with one open issues, and Actions without issues.
    Also get the list of well/not well maintained Actions.

    :param sqlite_cursor: The cursor for the database connection.
    :return: The list of well and the list of not well maintained Actions.
    """
    actions = get_all_actions_names(sqlite_cursor)
    open_closed_query = """
    SELECT open, closed FROM issues WHERE owner=? AND repository=?;
    """

    not_well_maintained_actions = []
    one_open_issue = 0
    no_issues = 0
    well_maintained = []
    for owner, repository, _ in actions:
        open_issues, closed_issues = sqlite_cursor.execute(open_closed_query, (owner, repository)).fetchone()
        issues = open_issues + closed_issues
        if issues == 1 and open_issues == 1:
            one_open_issue += 1
        more_open_issues = open_issues > closed_issues
        if more_open_issues and closed_issues != 0:
            percentage = (open_issues / issues) * 100
            if percentage > 70:
                not_well_maintained_actions.append((owner, repository))
            else:
                well_maintained.append((owner, repository))
        elif more_open_issues:
            not_well_maintained_actions.append((owner, repository))
        elif issues == 0:
            no_issues += 1
        else:
            well_maintained.append((owner, repository))

    print(f"Number of not well maintained Actions: {len(not_well_maintained_actions)}")
    print(f"Number of Actions with one open issue: {one_open_issue}")
    print(f"Number of Actions without issue: {no_issues}")
    return well_maintained, not_well_maintained_actions


def number_of_issues(sqlite_cursor: sqlite3.Cursor, actions) -> None:
    """
    Print the number of issues for a list of Actions.

    :param sqlite_cursor: The cursor for the database connection.
    :param actions: The list of Actions for which printing issues. List is constituted of tuples(owner, repository)
    """
    number_of_issues_query = """
    SELECT open, closed FROM issues WHERE owner=? AND repository=?;
    """
    open_issues_list = []
    closed_issues_list = []
    for owner, repository in actions:
        open_closed = sqlite_cursor.execute(number_of_issues_query, (owner, repository)).fetchone()
        open_issues = open_closed[0]
        closed_issues = open_closed[1]
        open_issues_list.append(open_issues)
        closed_issues_list.append(closed_issues)

    compute_statistics(open_issues_list, "of open issues")
    seaborn.boxplot(y=open_issues_list)
    plt.show()
    compute_statistics(closed_issues_list, "of closed issues")
    seaborn.boxplot(y=closed_issues_list)
    plt.show()


def number_of_actions_with_issues(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of Actions with issues.

    :param sqlite_cursor: The cursor for the database connection.
    """
    actions_with_issues_query = """
    SELECT COUNT(*) FROM issues WHERE closed <> 0 OR open <> 0;
    """
    actions_with_issues = sqlite_cursor.execute(actions_with_issues_query).fetchone()[0]
    print(f"There is {actions_with_issues} Actions with issues (open or closed or both).")


def number_of_actions_with_open_issues(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of Actions with only open issues.

    :param sqlite_cursor: The cursor for the database connection.
    """
    actions_with_only_open_issues_query = """
    SELECT COUNT(*) FROM issues WHERE closed = 0 AND open <> 0;
    """
    actions_with_open_issues = sqlite_cursor.execute(actions_with_only_open_issues_query).fetchone()[0]
    print(f"There is {actions_with_open_issues} Actions with open issues and no closed ones.")


def number_of_actions_with_closed_issues(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of Actions with only closed issues.

    :param sqlite_cursor: The cursor for the database connection.
    """
    actions_with_only_closed_issues_query = """
    SELECT COUNT(*) FROM issues WHERE closed <> 0 AND open = 0;
    """
    actions_with_closed_issues = sqlite_cursor.execute(actions_with_only_closed_issues_query).fetchone()[0]
    print(f"There is {actions_with_closed_issues} Actions with closed issues and no open ones.")


def rq7() -> None:
    """
    Check the proportion of verified users on the Marketplace, the total number of users and the proportion of
    verified ones.
    """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()

    separator = "-" * 10

    count_number_of_actions(sqlite_cursor)
    print(separator)

    count_number_of_owners(sqlite_cursor)
    print(separator)

    count_verified_users(sqlite_cursor)
    print(separator)

    count_verified_actions(sqlite_cursor)
    print(separator)

    actions_with_metrics = get_actions_with_metrics(sqlite_cursor)
    popular_actions = n_most_popular_actions(actions_with_metrics, 10, sqlite_cursor)
    n_most_popular_verified(sqlite_cursor, popular_actions)
    print(separator)

    count_verified_categories = verified_per_categories(sqlite_cursor)
    percentages = []
    for category, verified, total in count_verified_categories:
        percent = round(verified / total * 100, 2)
        percentages.append((category, verified, total, percent))
    percentages.sort(key=lambda x: x[3], reverse=True)
    print(percentages)

    sqlite_connection.close()


def count_number_of_actions(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of Actions in the database.
    :param sqlite_cursor: The cursor for the database connection.
    """
    count_actions_query = """
    SELECT COUNT(*) FROM (SELECT DISTINCT owner, repository FROM actions);
    """
    number_of_actions = sqlite_cursor.execute(count_actions_query).fetchone()[0]
    print(f"Number of actions: {number_of_actions}")


def count_number_of_owners(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of owners in the database.
    :param sqlite_cursor: The cursor for the database connection.
    """
    count_owners_query = """
    SELECT COUNT(*) FROM (SELECT DISTINCT owner FROM actions);
    """
    number_of_owners = sqlite_cursor.execute(count_owners_query).fetchone()[0]
    print(f"Number of owners: {number_of_owners}")


def count_actions_per_owner(sqlite_cursor: sqlite3.Cursor) -> list:
    """
    Count the number of Actions per owners.

    :param sqlite_cursor: The cursor for the database connection.
    :return: A list with the number of Actions per owner.
    """
    owners = get_owners(sqlite_cursor)
    number_of_actions_per_owner = []
    for owner in owners:
        actions_per_owner_query = """
        SELECT COUNT(*) FROM (SELECT DISTINCT owner, repository FROM actions WHERE owner=?);
        """
        actions_per_owner = sqlite_cursor.execute(actions_per_owner_query, (owner,)).fetchone()[0]
        number_of_actions_per_owner.append(actions_per_owner)
    number_of_actions_per_owner.sort()

    return number_of_actions_per_owner


def get_owners(sqlite_cursor: sqlite3.Cursor) -> list:
    """
    Get the list of owners.

    :param sqlite_cursor: The cursor for the database connection.
    :return: The list of owners.
    """
    owners_query = """
    SELECT DISTINCT owner FROM actions;
    """
    owners = sqlite_cursor.execute(owners_query).fetchall()
    owners = [owner[0] for owner in owners]

    return owners


def compute_statistics(values_list: list, end_of_sentence: str) -> None:
    """
    Print the median, maximum, minimum, q1, q3 of a list.
    :param values_list: The list with the values.
    :param end_of_sentence: The end of the sentence that will be printed.
    """
    median = statistics.median(values_list)
    maximum = max(values_list)
    minimum = min(values_list)
    q1 = numpy.percentile(values_list, 25)
    q3 = numpy.percentile(values_list, 75)
    iqr = q3 - q1

    print(f"Median {end_of_sentence}: {median}")
    print(f"Maximum {end_of_sentence}: {maximum}")
    print(f"Minimum {end_of_sentence}: {minimum}")
    print(f"Q1 {end_of_sentence}: {q1}")
    print(f"Q3 {end_of_sentence}: {q3}")
    print(f"IQR {end_of_sentence}: {iqr}")


def count_verified_users(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of verified users.

    :param sqlite_cursor: The cursor for the database connection.
    """
    number_of_verified_owners_query = """
    SELECT COUNT(DISTINCT owner) FROM actions WHERE verified=0;
    """
    number_of_verified_owners = sqlite_cursor.execute(number_of_verified_owners_query).fetchone()[0]
    print(f"Number of verified owners: {number_of_verified_owners}")


def count_verified_actions(sqlite_cursor: sqlite3.Cursor) -> None:
    """
    Print the number of Actions published by verified users.

    :param sqlite_cursor: The cursor for the database connection.
    """
    number_of_verified_actions_query = """
    SELECT COUNT(name) FROM actions WHERE verified=0;
    """
    number_of_verified_actions = sqlite_cursor.execute(number_of_verified_actions_query).fetchone()[0]
    print(f"Number of verified Actions: {number_of_verified_actions}")


def n_most_popular_verified(sqlite_cursor: sqlite3.Cursor, popular_actions: list) -> None:
    """
    Print the number of verified Actions among the list of most popular ones.

    :param sqlite_cursor: The cursor for the database connection.
    :param popular_actions: List of most popular Actions
    """
    check_verified_query = """
    SELECT verified FROM actions WHERE owner=? AND repository=?;
    """
    number_of_verified = 0
    number_of_unverified = 0
    for action_tuple in popular_actions:
        owner, repository, _ = action_tuple[0]
        verified = sqlite_cursor.execute(check_verified_query, (owner, repository)).fetchone()[0]
        # well, I chose 0 as "verified"... I leave it like this.
        is_verified = verified == 0
        if is_verified:
            number_of_verified += 1
        else:
            number_of_unverified += 1

    print(f"Verified popular Actions: {number_of_verified} / {len(popular_actions)}")
    print(f"Unverified popular Actions: {number_of_unverified} / {len(popular_actions)}")


def verified_per_categories(sqlite_cursor: sqlite3.Cursor) -> list:
    """
    Get the list with the number of verified Actions per categories.

    :param sqlite_cursor: The cursor for the database connection.
    :return: List of categories with their number of verified Actions.
    """
    verified_in_category = """
    SELECT COUNT(*) FROM
    (SELECT actions.owner, actions.repository, actions.verified, categories.category
    FROM actions, categories 
    WHERE actions.owner=categories.owner AND actions.repository=categories.repository
    AND actions.verified=0 AND categories.category=?);
    """
    categories_verified_total = []
    for category in categories_main:
        number_of_verified = sqlite_cursor.execute(verified_in_category, (category,)).fetchone()[0]
        total_actions = count_actions_for_category(sqlite_cursor, category)
        categories_verified_total.append((category, number_of_verified, total_actions))
    return categories_verified_total


def count_actions_for_category(sqlite_cursor: sqlite3.Cursor, category: str) -> int:
    """
    Get the number of Actions for a category.

    :param sqlite_cursor: The cursor for the database connection.
    :param category: The category.
    :return: The number of Actions in the category.
    """
    count_actions_category = """
    SELECT COUNT(*) FROM categories WHERE category=?;
    """
    number_of_actions = sqlite_cursor.execute(count_actions_category, (category,)).fetchone()[0]
    return number_of_actions


def rq8():
    """
    Observe the triggers used in workflow files.
    """
    number_of_repositories = config.rq8_number_of_repositories
    yml_file = f"outputs/yml_files_{number_of_repositories}.npy"

    already_fetch_yml_files = os.path.exists(yml_file)
    if not already_fetch_yml_files:
        print("You should get YML files with RQ4 first.")
        exit()

    list_of_workflow_files_contents = numpy.load(yml_file)
    actions_triggers_in_workflows = get_actions_triggers_in_workflows(list_of_workflow_files_contents)
    actions_triggers_in_workflows = sorted(actions_triggers_in_workflows.items(), key=lambda x: x[1], reverse=True)
    actions_triggers_in_workflows = dict(actions_triggers_in_workflows)
    number_of_triggers = get_triggers(actions_triggers_in_workflows)
    print(actions_triggers_in_workflows)
    print(number_of_triggers)
    total_triggers = 0
    for trigger in number_of_triggers:
        total_triggers += number_of_triggers[trigger]
    print(f"Total number of triggers: {total_triggers}")


def get_actions_triggers_in_workflows(workflow_files: numpy.ndarray) -> dict:
    """
    Get the list of workflow files and returns the times each Action has been triggered and the kind of trigger.
    The key of the returned dictionary is a tuple (trigger, category) and the key is an int representing the times
    triggered.

    :param workflow_files: The list of workflow files.
    :return: The times each Action has been triggered and the kind of trigger in a dictionary.
    """
    sqlite_connection = sqlite3.connect(f"{files_path_main}/{last_file_name_main}")
    sqlite_cursor = sqlite_connection.cursor()

    list_of_actions_on_marketplace = get_all_actions_names(sqlite_cursor)
    list_of_actions_on_marketplace = [f"{action[0]}/{action[1]}" for action in list_of_actions_on_marketplace]

    triggers_categories_counter = {}
    for workflow_content in workflow_files:
        pre_content = workflow_content.replace("on:", "trigger:").replace("\t", "    ")
        pre_content = re.sub(r"\n+", "\n", pre_content)
        content = yaml.safe_load(pre_content)
        if content and "jobs" in content.keys() and "trigger" in content.keys():
            triggers = []
            if type(content["trigger"]) is dict:
                triggers = content["trigger"].keys()
            elif type(content["trigger"]) is list:
                triggers = content["trigger"]
            elif type(content["trigger"]) is str:
                triggers = [content["trigger"]]
            jobs = content["jobs"]
            for job in jobs:
                if "steps" in jobs[job].keys():
                    steps = jobs[job]["steps"]
                    for step in steps:
                        step_keys = step.keys()
                        for key in step_keys:
                            if key == "uses":
                                use = step[key]
                                if "@" in use:
                                    use = use.split("@")[0]
                                    if use in list_of_actions_on_marketplace:
                                        for trigger in triggers:
                                            owner, repository = use.split("/")
                                            categories = get_categories_of_action(sqlite_cursor, (owner, repository))
                                            for category in categories:
                                                dictionary_key = (trigger, category)
                                                if dictionary_key not in triggers_categories_counter:
                                                    triggers_categories_counter[dictionary_key] = 1
                                                else:
                                                    triggers_categories_counter[dictionary_key] += 1

    sqlite_connection.close()

    return triggers_categories_counter


def get_triggers(actions_triggers_in_workflows: dict) -> dict:
    """
    Get the times a trigger has been set.

    :param actions_triggers_in_workflows: The dictionary with the number of times an Action has been triggered.
    :return: The times each trigger has been set.
    """
    triggers_counters = {}
    for key in actions_triggers_in_workflows:
        trigger = key[0]
        number = actions_triggers_in_workflows[key]
        if trigger not in triggers_counters:
            triggers_counters[trigger] = number
        else:
            triggers_counters[trigger] += number
    return triggers_counters


if __name__ == "__main__":
    files_path_main = config.files_path
    files_names_main = [file for file in os.listdir(files_path_main) if ".db" in file]
    files_names_main.sort()

    first_file_name_main = files_names_main[0]
    last_file_name_main = files_names_main[-1]

    categories_main = [
        'api-management',
        'chat',
        'code-quality',
        'code-review',
        'continuous-integration',
        'dependency-management',
        'deployment',
        'ides',
        'learning',
        'localization',
        'mobile',
        'monitoring',
        'project-management',
        'publishing',
        # 'recently-added',
        'security',
        'support',
        'testing',
        'utilities'
    ]

    if config.rq1:
        rq1()

    if config.rq2:
        rq2()

    if config.rq3:
        rq3()

    if config.rq4:
        rq4()

    if config.rq5:
        rq5()

    if config.rq6:
        rq6()

    if config.rq7:
        rq7()

    if config.rq8:
        rq8()
