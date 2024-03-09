from django.shortcuts import render

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://us.pycon.org/2024/schedule/"
HTML_FILE = "schedule.html"


def get_data(request):
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


def index(request):
    return render(request, "index.html")
