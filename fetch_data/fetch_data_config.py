"""
Configuration file for "fetch_data.py".
"""
import os

run = True

fetch_categories = {
    "versions": True,
    "dependents": True,
    "contributors": True,
    "stars": True,
    "watchers": True,
    "forks": True,
    "issues": True,
}

# used for debugging
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

tokens = [
    os.getenv("GITHUB_TOKEN1"),
    os.getenv("GITHUB_TOKEN2"),
    os.getenv("GITHUB_TOKEN3"),
    os.getenv("GITHUB_TOKEN4"),
]

limit_requests = 350
