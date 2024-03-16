import os
import re
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from django.shortcuts import render
from django.core.handlers.wsgi import WSGIRequest

import httpx
from bs4 import BeautifulSoup

from .models import Event, Presenter, TableUpdate

BASE_URL = "https://us.pycon.org"
SCHEDULES_URL = f"{BASE_URL}/2024/schedule/"
RESULTS_DIR = "site_data"


def get_context():
    """
    Gets the context for the index page.
    """
    events_exist = TableUpdate.objects.filter(table_name="EventsExist").exists()
    events_data = Event.objects.all().order_by('start_time')

    events_wednesday = []
    events_thursday = []
    events_friday = []
    events_saturday = []
    events_sunday = []

    for event in events_data:
        presenters = event.presenters.all()
        presenters_str = ", ".join([p.name for p in presenters])

        day = event.start_time.strftime("%A")
        event_info = {
            "title": event.title,
            "description": event.description,
            "day": day,
            "start_time": event.start_time.strftime("%I:%M %p"),
            "end_time": event.end_time.strftime("%I:%M %p"),
            "location": event.location,
            "presenters": presenters_str
        }
        if day == "Wednesday":
            events_wednesday.append(event_info)
        elif day == "Thursday":
            events_thursday.append(event_info)
        elif day == "Friday":
            events_friday.append(event_info)
        elif day == "Saturday":
            events_saturday.append(event_info)
        elif day == "Sunday":
            events_sunday.append(event_info)
        else:
            print("Error: Day not found.")

    context = {
        "events_wednesday": events_wednesday,
        "events_thursday": events_thursday,
        "events_friday": events_friday,
        "events_saturday": events_saturday,
        "events_sunday": events_sunday,
        "events_exist": events_exist,
    }
    return context


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
    total = len(links)
    for i, link in enumerate(links):
        filename = link.split("/")[-2].strip() + ".html"
        print(f"Downloading {filename} ({i}/{total})")
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
        TableUpdate.objects.update_or_create(table_name="EventsExist")

    context = get_context()
    context["message"] = message

    return render(request, "index.html", context=context)


def parse_time(time_str: str) -> datetime:
    """
    Helper function to parse the time string. Handles special values like "NOON".

    :param time_str: The time string to parse. Expected format examples:
        "2 PM", "2:30 PM", "NOON"
    :return: A datetime object representing the time.
    """
    if time_str == "NOON":
        time_str = "12 PM"

    try:
        result = datetime.strptime(time_str, "%I:%M %p")
    except ValueError:
        result = datetime.strptime(time_str, "%I %p")

    return result


def get_timestamps(day_str: str, time_str: str):
    """
    Parses the time string and returns the start and end times.
    Must be within Wed-Sun.

    :param day_str: The date string to parse. Expected format: "Wednesday"
    :param time_str: The time string to parse. Expected format: "2 p.m.-2:30 p.m."
    :return:
    """
    dates = {
        "Wednesday": "2024-05-15",
        "Thursday": "2024-05-16",
        "Friday": "2024-05-17",
        "Saturday": "2024-05-18",
        "Sunday": "2024-05-19"
    }

    date_str = dates[day_str]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    start_time_str, end_time_str = tuple(x.upper() for x in time_str.replace(".", "").split("-"))

    start_time = parse_time(start_time_str)
    end_time = parse_time(end_time_str)

    start_timestamp = date_obj.replace(hour=start_time.hour, minute=start_time.minute)
    end_timestamp = date_obj.replace(hour=end_time.hour, minute=end_time.minute)

    start_time = start_timestamp.replace(tzinfo=ZoneInfo("America/New_York"))
    end_time = end_timestamp.replace(tzinfo=ZoneInfo("America/New_York"))

    # print("Start Timestamp:", start_time)
    # print("End Timestamp:", end_time)

    return start_time, end_time


def parse_schedule_data(soup: BeautifulSoup, event_id: int):
    """
    Parses the schedule data from the given soup object.
    Adds the data to the database.

    :param soup: The soup object containing the schedule data.
    :param event_id: The ID of the scheduled event.
    """
    print(f"Parsing schedule data for: {event_id}.html")
    panel_heading = soup.find("div", class_="panel-heading")
    heading = panel_heading.find("h3").text
    details = panel_heading.find("p").text

    day, details = details.split(" - ")
    event_times = details.split("2024 ")[1].split(" in")[0]

    location = details.split("in ")[1]
    # print("Details:", details)
    # print('---')
    # print("Day:", day)
    # print("Time:", event_time)
    # print("Location:", location)

    start_time, end_time = get_timestamps(day, event_times)

    panel_body = soup.find("div", class_="panel-body")
    presenter_details = panel_body.find_all("a", href=re.compile(r"^/2024/speaker/profile"))
    presenters = []
    for detail in presenter_details:
        # print("Detail:", detail)
        presenter_name = detail.text
        try:
            presenter_link = detail["href"]
        except TypeError:
            continue

        presenter_id = int(presenter_link.split("/")[-2])

        Presenter.objects.get_or_create(
            id=presenter_id,
            defaults={
                "name": presenter_name,
                "bio": ""
            }
        )
        presenters.append(presenter_id)

    description = soup.find("div", class_="description").text

    event, created = Event.objects.get_or_create(
        id=event_id,
        defaults={
            "title": heading,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location
        }
    )

    # Add the presenters to the event.
    for presenter_id in presenters:
        event.presenters.add(presenter_id)


def parse_data(request: WSGIRequest) -> render:
    """
    Parses the latest schedule data for all files in the results directory.
    """
    # Clear out the existing tables
    Event.objects.all().delete()
    Presenter.objects.all().delete()

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".html")]
    current_dir = os.path.abspath(RESULTS_DIR)

    # filename = "/code/site_data/20.html"
    # print(f"Parsing schedule data for: {filename}")
    # soup = read_html_file(filename)
    # event_id = 20
    # parse_schedule_data(soup, event_id)

    for file in files:
        filename = os.path.join(current_dir, file)
        try:
            event_id = int(file.split(".html")[0])
        except ValueError:
            event_id = 0

        soup = read_html_file(filename)
        parse_schedule_data(soup, event_id)

    # Update TableUpdate values with both Event and Presenter tables
    TableUpdate.objects.update_or_create(table_name="Event")
    TableUpdate.objects.update_or_create(table_name="Presenter")

    context = get_context()
    return render(request, "index.html", context=context)


def index(request):
    """
    Loads the home page.
    """
    context = get_context()
    return render(request, "index.html", context=context)
