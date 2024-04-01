from django.contrib import admin

from .models import Presenter, Event, TableUpdate


class TableUpdateAdmin(admin.ModelAdmin):
    list_display = ("table_name", "last_updated")


class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time", "location")


admin.site.register(Presenter)
admin.site.register(Event, EventAdmin)
admin.site.register(TableUpdate, TableUpdateAdmin)
