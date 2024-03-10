from typing import Optional

from django.shortcuts import render
from django.core.handlers.wsgi import WSGIRequest

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://us.pycon.org"
SCHEDULES_URL = f"{BASE_URL}/2024/schedule/"
RESULTS_DIR = "site_data"


def read_html_file(file_path) -> Optional[BeautifulSoup]:
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


def get_all_schedule_links() -> list[str]:
    """
    Gets all the schedule links from the main schedule page.

    :return: A list of schedule links.
    """
    response = httpx.get(BASE_URL + "/2024/schedule/")
    if response.status_code != 200:
        return []

    results = []
    soup = BeautifulSoup(response.content, 'html.parser')

    prefix = "/2024/schedule/presentation/"
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.startswith(prefix):
            results.append(href)

    for item in results:
        link = BASE_URL + item
        filename = item.split("/")[-2].strip() + ".html"
        print(f"{link} => {filename}")
        # response = httpx.get(link)
        # file_content_str = str(BeautifulSoup(response.content, 'html.parser'))
        #
        # with open(f"{RESULTS_DIR}/{filename}", 'w', encoding='utf-8') as file:
        #     file.write(file_content_str)

    return results


def get_data(request: WSGIRequest) -> render:
    """
    Gets the latest data from the website and saves the results.
    """
    links = get_all_schedule_links()

    if links:
        message = "Latest schedule data downloaded successfully! Ready to parse."
    else:
        message = "Error downloading schedule data. Please try again later."

    context = {
        "message": message,
        "results": links,
    }

    return render(request, "index.html", context=context)


def index(request):
    """
    Loads the home page.
    """
    return render(request, "index.html")
