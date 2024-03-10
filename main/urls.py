from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("get_data", views.get_data, name="get_data"),
    # path("parse_data", views.parse_data, name="parse_data"),
]
