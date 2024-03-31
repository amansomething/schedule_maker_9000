from django.contrib import admin

from .models import Presenter, Event, TableUpdate


class TableUpdateAdmin(admin.ModelAdmin):
    list_display = ("table_name", "last_updated")


admin.site.register(Presenter)
admin.site.register(Event)
admin.site.register(TableUpdate, TableUpdateAdmin)
