"""
Configuration file for "fetch_data.py".
"""
import os

run = True

fetch_categories = {
    "versions": False,
    "dependents": False,
    "contributors": True,
    "stars": False,
    "watchers": False,
    "forks": False,
    "issues": False,
}

# used for debugging
override_save_categories = {
    "run": True,
    "categories": ["code-review"],
}

get_categories = {
    "run": True,
}

fetch_data = {
    "run": True,
    "max_threads": 50,
}

tokens = [
    os.getenv("GITHUB_TOKEN1"),
    os.getenv("GITHUB_TOKEN2"),
    os.getenv("GITHUB_TOKEN3"),
    os.getenv("GITHUB_TOKEN4"),
]

limit_requests = 350
