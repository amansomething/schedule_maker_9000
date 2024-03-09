from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("get_data", views.get_data, name="get_data"),
]
