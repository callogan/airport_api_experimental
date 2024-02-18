import os
import uuid

import pytz
from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.db.models import Count, Max, Avg
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


class Airline(models.Model):
    name = models.CharField(max_length=255, verbose_name='Name')
    headquarter = models.CharField(max_length=255, verbose_name='Headquarter')
    web_site_address = models.URLField(verbose_name='Web-site Address')
    iata_icao = models.CharField(max_length=20, verbose_name='IATA/ICAO Codes')
    url_logo = models.URLField(blank=True, null=True, verbose_name='URL Logo')

    @property
    def overall_rating(self):
        # ratings = self.ratings.all()

        WEIGHTS = {
            'avg_boarding_deplaining': 0.05,
            'avg_crew': 0.2,
            'avg_services': 0.15,
            'avg_entertainment': 0.1,
            'avg_wi_fi': 0.05
        }
        #
        # boarding_deplaining_rating = self.airlinerating_set.aggregate(avg_rating=Avg("boarding_deplaining_rating"))["avg_rating"]
        # crew_rating = self.airlinerating_set.aggregate(avg_rating=Avg("crew_rating"))["avg_rating"]
        # entertainment_rating = self.airlinerating_set.aggregate(avg_rating=Avg("entertainment_rating"))["avg_rating"]
        # service_rating = self.airlinerating_set.aggregate(avg_rating=Avg("service_rating"))["avg_rating"]
        # wi_fi_rating = self.airlinerating_set.aggregate(avg_rating=Avg("wi_fi_rating"))["avg_rating"]

        rating_per_category = self.ratings.filter(airline=self) \
            .aggregate(
            avg_boarding_deplaining=Avg('boarding_deplaining_rating'),
            avg_crew=Avg('crew_rating'),
            avg_service=Avg('services_rating'),
            avg_entertainment=Avg('entertainment_rating'),
            avg_wi_fi=Avg('wi_fi_rating')
        )

        total_score = 0
        total_weight = 0

        result_dict = {'overall_rating': 0}

        for category, rating in rating_per_category.items():
            value = rating
            weight = WEIGHTS.get(category, 0)

            total_score += value * weight
            total_weight += weight

            # Добавляем рейтинг по каждой категории в словарь
            result_dict[category] = value

        if total_weight > 0:
            result_dict['overall_rating'] = total_score / total_weight

        return result_dict


class Route(models.Model):
    source = models.ForeignKey(Airport, related_name="source_routes", on_delete=models.CASCADE)
    destination = models.ForeignKey(
        Airport, related_name="destination_routes", on_delete=models.CASCADE
    )
    distance = models.IntegerField()
    airline = models.ForeignKey(Airline, related_name="routes", on_delete=models.SET_NULL, null=True)

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
    airline = models.ForeignKey(Airline, related_name="airplanes", on_delete=models.CASCADE)
    image = models.ImageField(null=True, upload_to=airplane_image_file_path)

    @property
    def total_rows(self):
        # Calculate the total number of distinct rows based on associated seats
        return self.seats.values('row').distinct().count()

    def rows_with_seat_count(self):
        return Seat.objects.filter(airplane_id=self.pk).values(
            "row"
        ).annotate(
            seat_count=Count('id')
        )

    @property
    def capacity(self):
        # rows = self.rows_with_seat_count()
        # total = 0
        # for row in rows:
        #     total += row['seat_count']

        return self.seats.count()


    def __str__(self) -> str:
        return self.name

    @staticmethod
    def validate_airplane(total_rows, total_seats, error):
        # total_rows = instance.total_rows
        # total_seats = instance.total_seats

        if total_rows <= 0 or total_seats <= 0:
            raise error({"error": "Total rows and total seats must be > 0"})

        if total_seats % total_rows != 0:
            raise error({"error": "Total seats must be divisible by total rows"})


    def clean(self):
        Airplane.validate_airplane(self, ValidationError)


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

    @property
    def tickets_available(self):
        # Получение связанных билетов для данного заказа
        tickets = Ticket.objects.filter(order=self)

        # Получение связанных полетов для билетов заказа
        flights = Flight.objects.filter(tickets__in=tickets)

        # Получение связанных самолетов для полетов
        airplanes = Airplane.objects.filter(flight__in=flights)

        # Получение количества сидений в каждом ряду
        rows_with_seat_count = airplanes.values('seats__row').annotate(seat_count=Count('id'))

        # Агрегированная функция count для билетов заказа
        sold_tickets = tickets.count()

        # Расчет доступных билетов
        total_seats = sum(row['seat_count'] for row in rows_with_seat_count)
        available_tickets = max(0, total_seats - sold_tickets)

        return available_tickets

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
    row = models.IntegerField(blank=True, null=True)
    seat = models.IntegerField(blank=True, null=True)
    flight = models.ForeignKey(Flight, related_name="tickets", on_delete=models.CASCADE)
    allocated = models.BooleanField(default=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='check-in-pending')

    # def clean(self):
    #     super().clean()
    #     airplane = self.flight.airplane
    #     if self.row > airplane.total_rows:
    #         raise ValidationError(f"Row {self.row} is greater than total rows in airplane {airplane}")
    #
    #     rows = airplane.get_rows_with_seat_count()
    #     if self.row in rows and rows[self.row] <= self.seat:
    #         raise ValidationError(f"Seat {self.seat} not available in row {self.row}")

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
    def validate_ticket(row, seat_number, flight, error_to_raise):
        airplane = flight.airplane

        if row is not None:
            # Check if row exists for the given aircraft
            matching_rows = Seat.objects.filter(
                airplane=airplane,
                row=row
            )

            if not matching_rows.exists():
                raise error_to_raise({
                    "row": f"Row number {row} does not exist for the specified airplane."
                })

            # Если row валиден, проверяем seat_number
            if seat_number is not None:
                matching_seats = matching_rows.filter(seat_number=seat_number)

                if not matching_seats.exists():
                    raise error_to_raise({
                        "seat": f"Seat number {seat_number} does not exist for the specified airplane and row {row}."
                    })

            seat = seat_number
            # Check if there are no existing tickets with the specified row and seat for the given flight
            existing_tickets = Ticket.objects.filter(flight=flight, seat=seat, row=row)
            if existing_tickets.exists():
                raise error_to_raise({
                    "row": f"Ticket with row number {row} and seat {seat} already exists for the specified flight."
                })
        else:
            # If both seat_number and row are None, consider it valid
            pass

    def __str__(self):
        return f"{str(self.flight)} (row: {self.row}, seat: {self.seat})"

    def allocate_seat(self):
        # automated allocation logic, for example, by check-in
        if self.type == 'check-in-pending':
            row, seat_number = self.get_last_available_seat()
            if row is not None and seat_number is not None:
                self.row = row  # Assigning the row to the ticket
                self.seat = seat_number  # Assigning the seat number to the ticket
                self.type = 'completed'
                self.save()

    def get_last_available_seat(self):
        airplane = self.flight.airplane

        # Assuming there is a related Seat model with a field seat_number
        # and it has a foreign key to Airplane
        rows = Seat.objects.filter(airplane=airplane).values_list('row', flat=True).distinct()

        # Iterate through each row
        for row in rows:
            booked_seats_in_row = Ticket.objects.filter(flight=self.flight, row=row)

            # max number of seat in row
            max_seat_in_row = self.get_max_seat_in_row()

            # first free seat in a row
            for seat_number in range(1, max_seat_in_row + 1):
                b = booked_seats_in_row.filter(seat=seat_number)
                print(b)
                if not booked_seats_in_row.filter(seat=seat_number).exists():
                    return row, seat_number
                    # Если свободное место найдено, выходим из цикла
                    break

            return None, None

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
            self.flight,
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

class AirlineRating(models.Model):

    SCORE_CHOICES = (
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (4, "4"),
        (5, "5"),
    )

    boarding_deplaining_rating = models.SmallIntegerField(choices=SCORE_CHOICES, default=0, blank=True, null=True)
    crew_rating = models.SmallIntegerField(choices=SCORE_CHOICES, default=0, blank=True, null=True)
    services_rating = models.SmallIntegerField(choices=SCORE_CHOICES, default=0, blank=True, null=True)
    entertainment_rating = models.SmallIntegerField(choices=SCORE_CHOICES, default=0, blank=True, null=True)
    wi_fi_rating = models.SmallIntegerField(choices=SCORE_CHOICES, default=0, blank=True, null=True)

    airline = models.ForeignKey(
        Airline, on_delete=models.CASCADE, related_name="ratings"
    )

