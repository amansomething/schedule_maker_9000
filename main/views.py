import os
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
    Schedule links follow the pattern: /2024/schedule/presentation/{NUMBER}/

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
            results.append(BASE_URL + href)

    return results


def download_schedule_data(links: list[str], output_dir: str = RESULTS_DIR) -> list[str]:
    """
    Downloads the schedule data from the given links and saves it to the given directory.

    :param links: The links to the schedule data.
    :param output_dir: The directory to save the files to.
    """
    errors = []
    for link in links:
        filename = link.split("/")[-2].strip() + ".html"
        print(f"Downloading {filename}")
        response = httpx.get(link)

        if response.status_code != 200:
            errors.append(link)
            continue

        file_content_str = str(BeautifulSoup(response.content, 'html.parser'))
        with open(f"{output_dir}/{filename}", 'w', encoding='utf-8') as file:
            file.write(file_content_str)

    return errors


def get_data(request: WSGIRequest) -> render:
    """
    Gets the latest data from the website and saves the results.
    """
    links = get_all_schedule_links()
    errors = download_schedule_data(links)

    if errors:
        message = errors
        print(errors)
    else:
        message = "Latest schedule data downloaded successfully! Ready to parse."

    context = {
        "message": message,
    }

    return render(request, "index.html", context=context)


def parse_schedule_data(soup: BeautifulSoup):
    """
    Parses the schedule data from the given soup object.
    """
    panel_heading = soup.find("div", class_="panel-heading")
    heading = panel_heading.find("h3").text
    details = panel_heading.find("p").text
    day, date = details.split(" - ")
    date, location = date.split(" in ")

    panel_body = soup.find("div", class_="panel-body")
    presenters = panel_body.find("li")

    description = soup.find("div", class_="description").text

    print(heading)
    print(day)
    print(date)
    print(location)
    print(description)
    print(presenters)


def parse_data(request: WSGIRequest) -> render:
    """
    Parses the latest schedule data for all files in the results directory.
    """
    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".html")]
    current_dir = os.path.abspath(RESULTS_DIR)
    filename = os.path.join(current_dir, files[0])

    print(filename)
    soup = read_html_file(filename)
    parse_schedule_data(soup)
    # for file in files:
    #     filename = os.path.join(RESULTS_DIR, file)
    #     soup = read_html_file(filename)
    #     print(soup)
    #     parse_schedule_data(soup)

    context = {}
    return render(request, "index.html", context=context)


def index(request):
    """
    Loads the home page.
    """
    return render(request, "index.html")
