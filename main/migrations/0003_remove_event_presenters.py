# Generated by Django 5.0.3 on 2024-09-22 22:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_alter_event_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='presenters',
        ),
    ]
