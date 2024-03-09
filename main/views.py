from typing import Optional

from django.shortcuts import render
from django.core.handlers.wsgi import WSGIRequest

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://us.pycon.org/2024/schedule/"
HTML_FILE = "schedule.html"


def read_html_file(file_path: str = HTML_FILE) -> Optional[BeautifulSoup]:
    """
    Reads the HTML file returns the contents as a soup object to be used by other functions.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            return soup
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None


def get_data(request: WSGIRequest) -> render:
    """
    Gets the latest data from the website and saves the results.
    """
    response = httpx.get(BASE_URL)
    if response.status_code != 200:
        context = {
            "message": "Issue refreshing data!"
        }
    else:
        soup = BeautifulSoup(response.content, 'html.parser')
        with open(HTML_FILE, 'w', encoding='utf-8') as file:
            file.write(str(soup))

        context = {
            "message": "Latest schedule data downloaded successfully! Ready to parse."
        }

    return render(request, "index.html", context=context)


def parse_data(request: WSGIRequest) -> render:
    """
    Parses the schedule data and displays the results.
    """
    soup = read_html_file()
    headings = [x.get_text() for x in soup.find_all("h3")]
    print(headings)

    return render(request, "index.html", context={"headings": headings})


def index(request):
    """
    Loads the home page.
    """
    return render(request, "index.html")
