from django.contrib import admin

from .models import Presenter, Event, TableUpdate

admin.site.register(Presenter)
admin.site.register(Event)
admin.site.register(TableUpdate)
