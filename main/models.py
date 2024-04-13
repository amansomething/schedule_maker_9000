from django.conf import settings
from django.db import models


class Presenter(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    presenters = models.ManyToManyField(Presenter)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class SelectEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    selected = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event')
        ]

    def __str__(self):
        return f"{self.event.title} - {self.user}"


class TableUpdate(models.Model):
    table_name = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Last update: {self.last_updated}"
