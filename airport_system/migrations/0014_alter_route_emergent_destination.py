# Generated by Django 5.0.1 on 2024-03-01 15:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0013_remove_flight_emergent_airport_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="route",
            name="emergent_destination",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="emergent_destination_routes",
                to="airport_system.airport",
            ),
        ),
    ]
