"""
This script is used to generate plots in order to analyse the data previously retrieved.
"""
from datetime import datetime
from packaging import version as packaging_version

import data_analysis_config as config
import json
import math
import matplotlib.pyplot as plt
import random
import seaborn
import statistics


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
        "29/04/2022": 0,
        "13/04/2022": 0,
        "10/05/2022": 0,
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


def determine_popularity():
    pass


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
