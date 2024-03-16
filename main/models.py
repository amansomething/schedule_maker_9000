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
