# Generated by Django 5.0.1 on 2024-03-01 15:07

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0012_rename_destination_route_standard_destination"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="flight",
            name="emergent_airport",
        ),
        migrations.RemoveField(
            model_name="flight",
            name="standard_airport",
        ),
    ]
