# Generated by Django 5.0.1 on 2024-03-08 17:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0018_route_distance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="route",
            name="distance",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
