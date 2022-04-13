"""
Configuration file for "fetch_data.py".
"""
run = True

fetch_categories = {
    "versions": False,
    "dependents": True,
    "contributors": False,
    "stars": False,
    "watchers": False,
    "forks": False,
}

override_save_categories = {
    "run": True,
    "categories": ["dependency-management"],
}

get_categories = {
    "run": True,
}

fetch_data = {
    "run": True,
    "max_threads": 50,
}

limit_requests = 350
