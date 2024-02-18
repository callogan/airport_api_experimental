from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from airport_system.models import (
    Flight, Airport, Route, Airline, Airplane, AirplaneType, Order,
    Ticket, Seat, City, Country
)


def allocate_url(ticket_id):
    return reverse("airport_system:ticket_allocate", args=[ticket_id])


class AuthenticatedTicketApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        cls.client.force_authenticate(cls.user)

        airline = Airline.objects.create(name="Test airline")
        cls.airplane = Airplane.objects.create(
            name="Test airplane",
            airline=airline,
            airplane_type=AirplaneType.objects.create(name="Test type"),
        )
        for seat_row in range(1, 21):
            for seat_number in range(1, 16):
                Seat.objects.create(
                    airplane=cls.airplane,
                    row=seat_row,
                    seat_number=seat_number,
                )
        country_source = Country.objects.create(name="UK")
        country_destination = Country.objects.create(name="France")
        closest_big_city_source = City.objects.create(name="London", country=country_source)
        closest_big_city_destination = City.objects.create(name="Paris", country=country_destination)
        airport = Airport.objects.create(
            name="Heathrow Airport",
            iata_code="LHR",
            closest_big_city=closest_big_city_source
        )
        route = Route.objects.create(
            source=airport,
            destination=Airport.objects.create(
                name="Charles de Gaulle Airport",
                iata_code="CDG",
                closest_big_city=closest_big_city_destination
            ),
            distance=500,
            airline=airline
        )
        cls.flight = Flight.objects.create(
            airplane=cls.airplane,
            route=route,
            departure_time=datetime(2024, 1, 10, 12, 30, 0),
            arrival_time=datetime(2024, 1, 10, 14, 30, 0),
            airport=airport,
            status="in-flight"
        )
        cls.flight.save()

        cls.order = Order.objects.create(user=cls.user)
        cls.ticket_allocated = Ticket(
            seat=1, row=1, flight=cls.flight, order=cls.order
        )
        cls.ticket_allocated.save()
        cls.ticket_not_allocated = Ticket(
            flight=cls.flight, order=cls.order
        )
        cls.ticket_not_allocated.save()


    def test_validate_ticket_with_wrong_seat(self):
        row = 18
        seat_number = 21
        message = f"Seat number {seat_number} does not exist for the specified airplane and row {row}."

        with self.assertRaisesMessage(ValidationError, message):
            self.ticket_allocated.validate_ticket(
                row, seat_number, self.flight, ValidationError
            )

    def test_validate_ticket_with_wrong_row(self):
        row = 35
        seat_number = 5
        message = f"Row number {row} does not exist for the specified airplane."

        with self.assertRaisesMessage(ValidationError, message):
            self.ticket_allocated.validate_ticket(
                row, seat_number, self.flight, ValidationError
            )

    def test_validate_ticket_with_valid_row_and_seat(self):
        row = 18
        seat_number = 5

        self.assertIsNone(
            self.ticket_allocated.validate_ticket(
                row, seat_number, self.flight, ValidationError
            )
        )


    def test_update_ticket_with_row_and_seat(self):
        ticket_id = self.ticket_not_allocated.id

        payload = {
            "row": 1,
            "seat": 2
        }

        res = self.client.patch(allocate_url(self.ticket_not_allocated.id), data=payload)

        # Обновляем тикет из базы данных
        self.ticket_not_allocated.refresh_from_db()

        # Проверяем результаты
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["row"], self.ticket_not_allocated.row)
        self.assertEqual(payload["seat"], self.ticket_not_allocated.seat)
