"""
Configuration file for "data_analysis.py"
"""
file_name = "outputs/actions_data_30_05_2022.json"
old_files_names = [
    # "outputs/actions_data_10_03_2022.json",
    # "outputs/actions_data_16_05_2022.json",
    "outputs/actions_data_25_03_2022.json",
    "outputs/actions_data_13_04_2022.json",
    "outputs/actions_data_29_04_2022.json",
    "outputs/actions_data_17_05_2022.json",
]

grow = {
    # "10/03/2022": 0,
    "25/03/2022": 0,
    "13/04/2022": 0,
    "29/04/2022": 0,
    # "16/05/2022": 0,
    "17/05/2022": 0,
    "30/05/2022": 0,
}

samples_to_make = 500

ymls_content = False

market_growing_over_time = False  # DONE
actions_diversity = False  # DONE
most_commonly_proposed = False  # DONE
actions_technical_lag = False  # DONE
actions_popularity = False  # DONE
multiple_actions = False  # DONE
actions_issues = True  # DONE
most_active_contributors = False  # DONE
compare_number_actions_officials_not_officials = False  # DONE
how_actions_triggered = False  # DONE
compare_number_of_versions = False  # DONE
compare_number_of_contributors = False  # DONE
do_actions_use_dependabot = False  # DONE
