from django.contrib import admin

from .models import Event, Presenter, SelectEvent, TableUpdate


class PresenterAdmin(admin.ModelAdmin):
    list_display = ("name", "bio")
    ordering = ("name",)


class TableUpdateAdmin(admin.ModelAdmin):
    list_display = ("table_name", "last_updated")


class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time", "location", "presenter_names")
    ordering = ("start_time",)
    search_fields = ("title", "location")


class SelectEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "selected")


admin.site.register(Presenter, PresenterAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(TableUpdate, TableUpdateAdmin)
admin.site.register(SelectEvent, SelectEventAdmin)
