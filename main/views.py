import os
import re
import zoneinfo
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils.timezone import activate, localtime
from django.shortcuts import render, redirect
from django.core.handlers.wsgi import WSGIRequest

import httpx
from bs4 import BeautifulSoup

from .models import Event, Presenter, TableUpdate

BASE_URL = "https://us.pycon.org"
SCHEDULES_URL = f"{BASE_URL}/2024/schedule/"
RESULTS_DIR = "site_data"


def get_valid_tzs(request: WSGIRequest) -> tuple[list[str], list[str]]:
    """
    Gets the valid timezones for the user to select from.
    Puts common US timezones at the top of the list.

    :return: A tuple of valid timezones and common timezones.
    """
    common_tzs = [
        "America/Los_Angeles",  # Pacific
        "America/Denver",  # Mountain
        "America/Chicago",  # Central
        "America/New_York",  # Eastern
    ]
    other_valid_tzs = sorted([x for x in zoneinfo.available_timezones() if x not in common_tzs])
    valid_tzs = common_tzs + other_valid_tzs

    return valid_tzs, common_tzs


def get_context(request: WSGIRequest):
    """
    Gets the context for the index page.
    """
    events_exist = TableUpdate.objects.filter(table_name="EventsExist").exists()
    events_data = Event.objects.all().order_by('start_time')
    tzs, common_tzs = get_valid_tzs(request)

    current_tz = request.session.get("django_timezone", "UTC")

    all_events = {
        "Wednesday": [],
        "Thursday": [],
        "Friday": [],
        "Saturday": [],
        "Sunday": [],
    }

    for event in events_data:
        presenters = event.presenters.all()
        presenters_str = ", ".join([p.name for p in presenters])

        day = event.start_time.strftime("%A")
        start_time = localtime(event.start_time)
        end_time = localtime(event.end_time)
        event_info = {
            "title": event.title,
            "description": event.description,
            "day": day,
            "start_time": start_time.strftime("%I:%M %p"),
            "end_time": end_time.strftime("%I:%M %p"),
            "location": event.location,
            "presenters": presenters_str
        }
        try:
            all_events[day].append(event_info)
        except IndexError:
            print("Error: Day not found.")

    context = {
        "all_events": all_events,
        "events_exist": events_exist,
        "tzs": tzs,
        "common_tzs": common_tzs,
        "current_tz": current_tz,
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
    If successful, also parses the data and fills the database.
    """
    links = get_all_schedule_links()
    errors = download_schedule_data(links)

    if errors:
        message = errors
        print(errors)
    else:
        errors = parse_data(request)
        if errors:
            message = errors
        else:
            message = "Latest schedule data downloaded and parsed successfully!"
        TableUpdate.objects.update_or_create(table_name="EventsExist")

    context = get_context(request)
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


def parse_schedule_data(soup: BeautifulSoup, event_id: int) -> Optional[list[str]]:
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

    errors = []

    # Add the presenters to the event.
    for presenter_id in presenters:
        try:
            event.presenters.add(presenter_id)
        except ValueError:
            errors.append(f"Error adding presenter {presenter_id} to event {event_id}")

    return errors


def parse_data(request: WSGIRequest) -> Optional[list[str]]:
    """
    Parses the latest schedule data for all files in the results directory.
    """
    errors = []

    # Clear out the existing tables
    Event.objects.all().delete()
    Presenter.objects.all().delete()

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".html")]
    if not files:
        print("Error: No files found in the results directory.")
        return errors

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
        error = parse_schedule_data(soup, event_id)
        if error:
            errors.extend(error)

    # Update TableUpdate values with both Event and Presenter tables
    TableUpdate.objects.update_or_create(table_name="Event")
    TableUpdate.objects.update_or_create(table_name="Presenter")

    if errors:
        print("Errors parsing schedule data:")
        for error in errors:
            print(f"\t{error}")

    return errors


def change_tz(request: WSGIRequest) -> redirect:
    """
    Changes the timezone for the user. Sets UTC as the default if an unsupported timezone is passed.
    Redirects to the homepage.
    """
    valid_tzs, _ = get_valid_tzs(request)

    tz = request.POST.get('select-tz')

    if tz and tz not in valid_tzs:
        tz = 'UTC'
    request.session['django_timezone'] = tz

    print(f"Timezone set to: {tz}")
    activate(tz)

    return redirect('home')


def select_events(request: WSGIRequest):
    """
    Loads the home page.
    """
    context = get_context(request)

    wed_events = Event.objects.filter(start_time__day=15).order_by('start_time')
    for event in wed_events:
        print(event.title, event.start_time)
    context["wed_events"] = wed_events

    return render(request, "select_events.html", context=context)


def index(request: WSGIRequest):
    """
    Loads the home page.
    """
    context = get_context(request)

    return render(request, "index.html", context=context)
