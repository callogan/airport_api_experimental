# Generated by Django 5.0.1 on 2024-02-22 15:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "airport_system",
            "0005_alter_airline_headquarter_alter_airline_iata_icao_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Crew",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=64)),
                ("last_name", models.CharField(max_length=64)),
            ],
        ),
        migrations.RenameField(
            model_name="flight",
            old_name="arrival_time",
            new_name="estimated_arrival_time",
        ),
        migrations.AddField(
            model_name="flight",
            name="real_arrival_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="flight",
            name="crews",
            field=models.ManyToManyField(
                related_name="flights", to="airport_system.crew"
            ),
        ),
    ]
