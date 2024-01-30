import os
import uuid

import pytz
from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.db.models import Count, Max
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError


# from rest_framework.exceptions import ValidationError


class Country(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "country"
        verbose_name_plural = "countries"


class City(models.Model):
    name = models.CharField(max_length=64)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "city"
        verbose_name_plural = "cities"


# def get_timezone_choices():
#     timezones = pytz.all_timezones
#     choices = []
#
#     for tz in timezones:
#         timezone = pytz.timezone(tz)
#         current_time = datetime.now()
#
#         # Локализация времени в выбранной тайм зоне
#         localized_time = timezone.localize(current_time)
#
#         # Нормализация времени (учитывает переход на летнее/зимнее время)
#         normalized_time = timezone.normalize(localized_time)
#
#         # Перевод времени в UTC (если оно в летнее время)
#         utc_time = normalized_time.astimezone(pytz.utc)
#
#         # Проверка, находится ли текущее время в летнем времени
#         is_dst = normalized_time.dst() != timedelta(0)
#
#         # Формирование строки с названием тайм зоны, учетом зимнего/летнего времени
#         if is_dst:
#             choices.append((tz, f'{tz} ({normalized_time.strftime("%z")} - {timezone.tzname(utc_time)})'))
#         else:
#             choices.append((tz, f'{tz} ({normalized_time.strftime("%z")} - {timezone.tzname(None)})'))
#
#     return choices
#
# class YourModel(models.Model):
#     timezone = models.CharField(max_length=63, default='UTC', choices=get_timezone_choices())


class Airport(models.Model):
    name = models.CharField(max_length=255)
    closest_big_city = models.ForeignKey(City, on_delete=models.CASCADE)
    iata_code = models.CharField(max_length=3, blank=True, null=True, unique=True)
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
    timezone = models.CharField(max_length=63, default='UTC', choices=TIMEZONE_CHOICES)

    def __str__(self) -> str:
        return f"{self.name} ({self.closest_big_city}) - {self.iata_code}"
    #
    # def current_local_time(self):
    #     local_timezone = pytz.timezone(self.timezone)
    #     return timezone.localtime(timezone.now(), local_timezone)


class Airlines(models.Model):
    name = models.CharField(max_length=255, verbose_name='Name')
    headquarter = models.CharField(max_length=255, verbose_name='Headquarter')
    web_site_address = models.URLField(verbose_name='Web-site Address')
    iata_icao = models.CharField(max_length=20, verbose_name='IATA/ICAO Codes')
    url_logo = models.URLField(blank=True, null=True, verbose_name='URL Logo')


class Route(models.Model):
    source = models.ForeignKey(Airport, related_name="source_routes", on_delete=models.CASCADE)
    destination = models.ForeignKey(
        Airport, related_name="destination_routes", on_delete=models.CASCADE
    )
    distance = models.IntegerField()
    airlines = models.ForeignKey(Airlines, related_name="routes", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.source.closest_big_city} - {self.destination.closest_big_city}"


class AirplaneType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name


def airplane_image_file_path(instance, filename):
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.name)}-{uuid.uuid4()}{extension}"

    return os.path.join("uploads", "airplanes", filename)


class Airplane(models.Model):
    name = models.CharField(max_length=255)
    airplane_type = models.ForeignKey(AirplaneType, on_delete=models.CASCADE)
    airline = models.ForeignKey(Airlines, related_name="airplanes", on_delete=models.CASCADE)
    image = models.ImageField(null=True, upload_to=airplane_image_file_path)

    @property
    def total_rows(self):
        # Calculate the total number of distinct rows based on associated seats
        return self.seats.values('row').count()

    def rows_with_seat_count(self):
        return Airplane.objects.filter(id=self.pk).values(
            'seats__row'
        ).annotate(
            seat_count=Count('id')
        )

    def __str__(self) -> str:
        return self.name

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row
    #
    # def get_rows_info(self):
    #     # Предположим, что airplanes - это queryset или список объектов Airplane
    #     airplanes = Airplane.objects.all()
    #
    #     # Используем словарь для хранения количества мест в каждом ряду
    #     rows_info = {}
    #
    #     for airplane in airplanes:
    #         rows_info[airplane.rows] = airplane.seats_in_row
    #
    #     return rows_info


class Seat(models.Model):
    row = models.IntegerField()
    seat_number = models.IntegerField()
    airplane = models.ForeignKey(Airplane, related_name="seats", on_delete=models.CASCADE)

    def __str__(self):
        return f"Row {self.row}, Seat {self.seat_number}"


class Flight(models.Model):

    STATUS_CHOICES = [
        ('in flight', 'In flight'),
        ('failed', 'Failed'),
        ('delayed', 'Delayed'),
        ('ahead', 'Ahead'),
    ]

    route = models.ForeignKey(Route, related_name="flights", on_delete=models.CASCADE)
    airplane = models.ForeignKey(Airplane, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    airport = models.ForeignKey(Airport, related_name="emergent_flights", to_field='id', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in flight')

    def __str__(self):
        return f"{self.route}; {self.departure_time} - {self.arrival_time}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} - {self.get_status_display()}"


class Ticket(models.Model):
    TYPE_CHOICES = [
        ('check-in-pending', 'Check-in-pending'),
        ('completed', 'Completed'),
    ]

    order = models.ForeignKey(Order, related_name="tickets", on_delete=models.CASCADE)
    row = models.IntegerField()
    seat = models.IntegerField()
    flight = models.ForeignKey(Flight, related_name="tickets", on_delete=models.CASCADE)
    allocated = models.BooleanField(default=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='check-in-pending')

    def clean(self):
        super().clean()
        airplane = self.flight.airplane
        if self.row > airplane.total_rows:
            raise ValidationError(f"Row {self.row} is greater than total rows in airplane {airplane}")

        rows = airplane.get_rows_with_seat_count()
        if self.row in rows and rows[self.row] <= self.seat:
            raise ValidationError(f"Seat {self.seat} not available in row {self.row}")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['row', 'seat', 'flight'], name='unique_row_seat_flight')
        ]
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=['row', 'seat', 'flight'], name='unique_row_seat_flight'),
    #         models.CheckConstraint(
    #             check=~models.Q(
    #                 flight__airplane__total_rows__contains={"row": models.F("row")},
    #                 flight__airplane__get_rows_with_seat_count__seats__lt=models.F("seat")
    #             ),
    #             name="validate_row_and_seat"
    #         )
    #     ]
        # ordering = ["row", "seat"]

    @staticmethod
    def validate_ticket(row, seat, airplane, flight, error_to_raise):
        # Your uniqueness validation is already handled by the database constraints.

        # Additional validation for range
        if seat < 1 or seat > airplane.seats_in_row:
            raise error_to_raise({
                "seat": f"Seat {seat} is not within the valid range for the airplane."
            })

        try:
            with transaction.atomic():
                Ticket.objects.create(flight=flight, row=row, seat=seat)
        except IntegrityError:
            raise error_to_raise({
                "row": f"Row {row} and seat {seat} combination violates constraints."
            })

    def __str__(self):
        return f"{str(self.flight)} (row: {self.row}, seat: {self.seat})"

    def allocate_seat(self):
        # authomated allocation logic, f. e. by check-in
        if not self.allocated:
            self.seat = self.flight.get_last_available_seat()
            self.allocated = True
            self.save()

    def get_last_available_seat(self):
        # all ticket for the flight
        booked_seats = Ticket.objects.filter(flight=self)

        # max number of seat in row
        max_seat_in_row = self.get_max_seat_in_row()

        # first free seat in a row
        for seat_number in range(1, max_seat_in_row + 1):
            if not booked_seats.filter(seat=seat_number).exists():
                return seat_number

        return None

    def get_max_seat_in_row(self):
        # Get the related Airplane for the current Ticket
        airplane = self.flight.airplane

        # Assuming there is a related Seat model with a field seat_number
        # and it has a foreign key to Airplane
        max_seat_in_row = (
            Seat.objects
            .filter(airplane=airplane)
            .values('row')
            .annotate(max_seat=Count('seat_number'))
            .aggregate(Max('max_seat'))
        )['max_seat__max']

        return max_seat_in_row

    def clean(self):
        Ticket.validate_ticket(
            self.row,
            self.seat,
            self.flight.airplane,
            ValidationError,
        )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.full_clean()

        if self.pk and force_update:
            super(Ticket, self).save(force_update=True,
                                     using=using,
                                     update_fields=update_fields)

        elif force_insert:
            super(Ticket, self).save(force_insert=True,
                                     using=using)
        else:
            super(Ticket, self).save(using=using,
                                     update_fields=update_fields)

class AirlineEvaluation(models.Model):
    SCORE_CHOICES = (
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    )
    airlines = models.ForeignKey(
        Airlines, on_delete=models.CASCADE, related_name="reviews_of"
    )
    rating = models.IntegerField(choices=SCORE_CHOICES)
