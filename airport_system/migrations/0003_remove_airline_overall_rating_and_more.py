# Generated by Django 5.0.1 on 2024-02-02 16:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("airport_system", "0002_alter_airline_boarding_deplaining_rating_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="airline",
            name="overall_rating",
        ),
        migrations.AlterField(
            model_name="airlinerating",
            name="airline",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ratings",
                to="airport_system.airline",
            ),
        ),
    ]
