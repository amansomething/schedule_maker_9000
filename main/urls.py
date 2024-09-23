from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("get_data", views.get_data, name="get_data"),
    path("parse_data", views.parse_data, name="parse_data"),
    path("change_tz", views.change_tz, name="change_tz"),
    path("select_events", views.select_events, name="select_events"),
    path("select_event/<event_id>", views.select_event, name="select_event"),
    path("selected_events", views.selected_events, name="selected_events"),
]
