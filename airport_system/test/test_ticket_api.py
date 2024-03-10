from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from airport_system.models import (
    Flight, Airport, Route, Airline, Airplane, AirplaneType, Order,
    Ticket, Seat, City, Country, Crew
)


def allocate_url(ticket_id):
    return reverse("airport_system:ticket_allocate", args=[ticket_id])


class AuthenticatedTicketApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password",
        )
        refresh = RefreshToken.for_user(cls.user)
        cls.token = refresh.access_token
        cls.client.credentials(HTTP_AUTHORIZATION=f"Bearer {cls.token}")

        cls.airline = Airline.objects.create(name="Test airline")
        cls.airplane = Airplane.objects.create(
            name="Test airplane",
            airline=cls.airline,
            airplane_type=AirplaneType.objects.create(name="Test type"),
        )
        for seat_row in range(1, 21):
            for seat_number in range(1, 16):
                Seat.objects.create(
                    airplane=cls.airplane,
                    row=seat_row,
                    seat_number=seat_number,
                )
        country_source = Country.objects.create(name="USA")
        country_destination = Country.objects.create(name="Germany")
        closest_big_city_source = City.objects.create(name="New York", country=country_source)
        closest_big_city_destination = City.objects.create(name="Berlin", country=country_destination)
        airport = Airport.objects.create(
            name="John F. Kennedy International Airport",
            iata_code="JFK",
            closest_big_city=closest_big_city_source
        )
        route = Route.objects.create(
            source=airport,
            standard_destination=Airport.objects.create(
                name="Berlin Tegel Airport 'Otto Lilienthal'",
                iata_code="TXL",
                closest_big_city=closest_big_city_destination
            ),
            airline=cls.airline
        )
        cls.flight = Flight.objects.create(
            airplane=cls.airplane,
            route=route,
            departure_time=datetime(2024, 1, 10, 12, 30, 0),
            estimated_arrival_time=datetime(2024, 1, 10, 14, 30, 0),
            status="in-flight"
        )

        crew = Crew.objects.create(first_name="John", last_name="Doe")
        cls.flight.crew.add(crew.id)
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

    def test_validate_ticket_wrong_seat(self):
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
        payload = {
            "row": 1,
            "seat": 2
        }

        res = self.client.patch(allocate_url(self.ticket_not_allocated.id), data=payload)

        self.ticket_not_allocated.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["row"], self.ticket_not_allocated.row)
        self.assertEqual(payload["seat"], self.ticket_not_allocated.seat)

    #TEMPORARY CODE
    def test_unique_row_seat_flight(self):
        # Тест уникальности комбинаций row, seat и flight
        airline = Airline.objects.create(name="Test airline")
        country_source = Country.objects.create(name="Portugal")
        country_destination = Country.objects.create(name="Poland")
        closest_big_city_source = City.objects.create(
            name="Lisbon", country=country_source
        )
        closest_big_city_destination = City.objects.create(
            name="Warsaw", country=country_destination
        )
        route_3 = Route.objects.create(
            source=Airport.objects.create(
                name="Humberto Delgado Airport",
                iata_code="LIS",
                closest_big_city=closest_big_city_source
            ),
            standard_destination=Airport.objects.create(
                name="Warsaw Chopin Airport",
                iata_code="WAW",
                closest_big_city=closest_big_city_destination,
            ),
            airline=airline
        )
        # crew = Crew.objects.create(first_name="Julie", last_name="Harrington")
        airplane = Airplane.objects.create(
            name="Test airplane",
            airline=airline,
            airplane_type=AirplaneType.objects.create(name="Test type"),
        )
        for seat_row in range(1, 21):
            for seat_number in range(1, 16):
                Seat.objects.create(
                    airplane=airplane,
                    row=seat_row,
                    seat_number=seat_number,
                )
        flight_1 = Flight.objects.create(
            airplane=airplane,
            route=route_3,
            departure_time="2022-06-02 14:00",
            estimated_arrival_time="2022-06-02 20:00"
        )
        order = Order.objects.create(user=self.user)
        obj1 = Ticket(row=1, seat=1, flight=flight_1, order=order)
        obj1.save()

        obj2 = Ticket(row=1, seat=1, flight=flight_1, order=order)
        try:
            obj2.save()
            self.fail("Expected an exception but none was raised")  # If no exception is raised, fail the test
        except Exception as e:
            print(f"Тип исключения: {type(e)}")
            print(f"Сообщение исключения: {e}")
