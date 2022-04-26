"""
Configuration file for "fetch_data.py".
"""
run = True

fetch_categories = {
    "versions": True,
    "dependents": True,
    "contributors": True,
    "stars": True,
    "watchers": True,
    "forks": True,
}

override_save_categories = {
    "run": False,
    "categories": ["recently-added", "security"],
}

get_categories = {
    "run": True,
}

fetch_data = {
    "run": True,
    "max_threads": 50,
}

limit_requests = 350
