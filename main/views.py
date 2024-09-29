import os
import zoneinfo
from typing import Optional
from zoneinfo import ZoneInfo

import yaml
from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import activate, localtime
from django.views.decorators.http import require_POST

from .models import Event, Presenter, SelectEvent, TableUpdate


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
    other_valid_tzs = sorted(
        [x for x in zoneinfo.available_timezones() if x not in common_tzs]
    )
    valid_tzs = common_tzs + other_valid_tzs

    return valid_tzs, common_tzs


def get_context(request: WSGIRequest):
    """
    Gets the context info needed to display various pages including:
        - Whether events have been added to the database.
        - A list of events from the database.
        - A list of selected events from the database.
        - A list of valid timezones.
    """
    events_exist = TableUpdate.objects.filter(table_name="EventsExist").exists()
    events_data = Event.objects.all().order_by("start_time")
    tzs, common_tzs = get_valid_tzs(request)

    current_tz = request.session.get("django_timezone", "UTC")

    all_events = {
        "Monday": [],
        "Tuesday": [],
        "Wednesday": [],
    }

    for event in events_data:
        day = event.start_time.strftime("%A")
        start_time = localtime(event.start_time)
        end_time = localtime(event.end_time)
        event_info = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "day": day,
            "start_time": start_time.strftime("%I:%M %p"),
            "end_time": end_time.strftime("%I:%M %p"),
            "location": event.location,
            "selected": (
                "checked"
                if SelectEvent.objects.filter(
                    user=request.user, event=event, selected=True
                ).exists()
                else ""
            ),
        }
        try:
            all_events[day].append(event_info)
        except IndexError:
            print("Error: Day not found.")

    all_selected_events_raw = SelectEvent.objects.filter(
        user=request.user, selected=True
    ).order_by("event__start_time")

    all_selected_events = []
    for event in all_selected_events_raw:
        e = event.event
        event_info = {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "day": e.start_time.strftime("%A"),
            "start_time": localtime(e.start_time).strftime("%I:%M %p"),
            "end_time": localtime(e.end_time).strftime("%I:%M %p"),
            "location": e.location,
        }
        all_selected_events.append(event_info)

    context = {
        "all_events": all_events,
        "all_selected_events": all_selected_events,
        "events_exist": events_exist,
        "tzs": tzs,
        "common_tzs": common_tzs,
        "current_tz": current_tz,
    }
    return context


@login_required(login_url="/admin/login/?next=/get_data")
def get_data(request: WSGIRequest) -> render:
    """
    Gets the latest data from talks folder saves the results.
    If successful, also parses the data and fills the database.
    """
    errors = None

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


def read_filenames(directory: str, extension: str = None) -> list[str]:
    """
    Reads all filenames in a directory.

    :param directory: Directory to read filenames from.
    :param extension: Optional extension to filter by. Example: ".md"
    :return: A list of filenames, if any.
    """
    if extension:
        try:
            return [f for f in os.listdir(directory) if f.endswith(extension)]
        except FileNotFoundError:
            return []

    try:
        return [f for f in os.listdir(directory)]
    except FileNotFoundError:
        return []


def parse_presenter_data(presenters_dir: str = "presenters") -> list:
    """
    Parses the latest presenter data and adds to the database.

    :param presenters_dir: Directory where the presenter info is located.
    :return: A list of errors if any occurred. Otherwise, an empty list.
    TODO: Fix the issue with loading bio data for Jacob and Simon.
    """
    errors = []

    current_dir = os.path.abspath(presenters_dir)
    files = read_filenames("presenters", ".md")
    if not files:
        return ["Error: No files found in the presenters directory."]

    presenters = []
    for file in files:
        try:
            presenter_id = file.split(".md")[0]
        except ValueError:
            presenter_id = "0"

        filename = os.path.join(current_dir, file)
        print(f"Parsing: {filename}")

        try:
            with open(filename, "r") as f:
                data = yaml.safe_load_all(f)
                attributes = next(data)
                name = attributes.get("name", "ERROR")
                try:
                    bio = next(data)
                except Exception as e:
                    print(e)
                    bio = "ERROR"
        except FileNotFoundError:
            errors.append(f"Error: File not found: {filename}")
            continue
        except yaml.YAMLError as e:
            errors.append(f"Error: {e}")
            continue

        presenters.append(Presenter(id=presenter_id, name=name, bio=bio))

    if presenters:
        Presenter.objects.all().delete()
        Presenter.objects.bulk_create(presenters)
        TableUpdate.objects.update_or_create(table_name="PresentersExist")
    else:
        errors.append("Error: No presenter data found.")

    return errors


def parse_event_data(events_dir: str = "talks") -> list:
    """
    Parses the latest event data and adds to the database.

    :param events_dir: Directory where the event info is located.
    :return: A list of errors if any occurred. Otherwise, an empty list.
    TODO: Fix parsing issues with descriptions with things like colons.
    """
    errors = []

    current_dir = os.path.abspath(events_dir)
    files = read_filenames("talks", ".md")
    if not files:
        return ["Error: No files found in the talks directory."]

    events = []
    for file in files:
        try:
            event_id = file.split(".md")[0]
        except ValueError:
            event_id = "0"

        filename = os.path.join(current_dir, file)
        print(f"Parsing: {filename}")

        try:
            with open(filename, "r") as f:
                data = yaml.safe_load_all(f)
                attributes = next(data)
                title = attributes.get("title", "ERROR")
                start_time = attributes.get("start_datetime", "ERROR")
                end_time = attributes.get("end_datetime", "ERROR")
                location = attributes.get("room", "ERROR")
                try:
                    description = next(data)
                except Exception as e:
                    print(e)
                    description = "ERROR"

        except FileNotFoundError:
            errors.append(f"Error: File not found: {filename}")
            continue
        except yaml.YAMLError as e:
            errors.append(f"Error: {e}")
            continue

        start_time = start_time.replace(tzinfo=ZoneInfo("America/New_York"))
        end_time = end_time.replace(tzinfo=ZoneInfo("America/New_York"))

        events.append(
            Event(
                id=event_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=location,
            )
        )

    if events:
        Event.objects.all().delete()
        Event.objects.bulk_create(events)
        TableUpdate.objects.update_or_create(table_name="EventsExist")
    else:
        errors.append("Error: No event data found.")

    return errors


def parse_data(request: WSGIRequest) -> Optional[list[str]]:
    """
    Parses the latest schedule data for all files in the talks directory.
    """
    errors = []

    presenter_errors = parse_presenter_data()
    if presenter_errors:
        errors.extend(presenter_errors)

    events_errors = parse_event_data()
    if events_errors:
        errors.extend(events_errors)

    # Note when event data was last updated
    TableUpdate.objects.update_or_create(table_name="Event")

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

    tz = request.POST.get("select-tz")

    if tz and tz not in valid_tzs:
        tz = "UTC"
    request.session["django_timezone"] = tz

    print(f"Timezone set to: {tz}")
    activate(tz)

    return redirect("home")


@login_required(login_url="/admin/login/?next=/select_events")
def select_events(request: WSGIRequest):
    """
    Loads the page where all events are shown that can then be added to favorites.
    """
    context = get_context(request)
    return render(request, "select_events.html", context=context)


@require_POST
def select_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_event, _ = SelectEvent.objects.get_or_create(user=request.user, event=event)

    # Toggle the selection status
    user_event.selected = not user_event.selected
    user_event.save()

    # Return a new checkbox based on the new selection status
    checked_attribute = "checked" if user_event.selected else ""
    html = f"""<input type="checkbox" hx-post="/select_event/{event_id}" hx-trigger="change"
                      hx-target="#event{event_id}" hx-swap="outerHTML"
                      id="event{event_id}" {checked_attribute}>"""

    return HttpResponse(html)


@login_required(login_url="/admin/login/?next=/selected_events")
def selected_events(request: WSGIRequest):
    """
    Loads the page where all selected events are shown.
    """
    context = get_context(request)

    return render(request, "selected_events.html", context=context)


@login_required(login_url="/admin/login/?next=/home")
def index(request: WSGIRequest):
    """
    Loads the home page.
    """
    context = get_context(request)

    return render(request, "index.html", context=context)
