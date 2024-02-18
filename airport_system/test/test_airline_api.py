from django.contrib.auth import get_user_model

from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


from airport_system.models import (
    Airline, Flight, Airplane, AirplaneType, Airport, Route, Seat, AirlineRating, Country, City
)

AIRLINE_URL = reverse("airport_system:airline-list")
AIRLINE_RATING_URL = reverse("airport_system:rating-list")
FLIGHT_URL = reverse("airport_system:flight-list")


def sample_airline(**kwargs):
    initial_data = {
        "name": "Airline 1",
    }
    initial_data.update(kwargs)

    return Airline.objects.create(**initial_data)

def sample_flight(**kwargs): #rename
    airplane_type = AirplaneType.objects.create(name="Exec Type")
    airline = kwargs.pop("airline")
    airplane = Airplane.objects.create(
        name="Flash", airline=airline, airplane_type=airplane_type
    )
    for seat_row in range(1, 21):
        for seat_number in range(1, 16):
            Seat.objects.create(
                airplane=airplane,
                row=seat_row,
                seat_number=seat_number,
            )

    country_source = Country.objects.create(name="UK")
    closest_big_city_source = City.objects.create(name="London", country=country_source)
    source = Airport.objects.create(name="Source airport", iata_code="WAV", closest_big_city=closest_big_city_source)
    country_destination = Country.objects.create(name="France")
    closest_big_city_destination = City.objects.create(name="Paris", country=country_destination)
    destination = Airport.objects.create(
        name="Destination airport", iata_code="FAT", closest_big_city=closest_big_city_destination
    )
    airport = source
    route = Route.objects.create(
        source=source, destination=destination, distance=1200
    )

    initial_data = {
        "airport": airport,
        "departure_time": "2023-02-16 14:00:00",
        "arrival_time": "2023-02-17 20:00:00",
        "airplane": airplane,
        "route": route,
    }
    initial_data.update(kwargs)

    return Flight.objects.create(**initial_data)


class AdminAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "test password", is_staff=True
        )
        self.airline = sample_airline()
        self.flight = sample_flight(airline=self.airline)
        self.flight.save()

    def test_create_airline(self):
        payload = {
            "name": "Airline 2",
        }
        res = self.client.post(AIRLINE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airline = Airline.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(airline, key))

    def test_create_airline_rating(self):
        airline = Airline.objects.create(
            name='Pan American',
            headquarter='Boston',
            web_site_address='https://www.united.com/',
            iata_icao='1234',
            url_logo='https://uk.wikipedia.org/wiki/%D0%A4%D0%B0%D0%B9%D0%BB:Delta_A350-900_N503DN_landing_ATL_runway_8L.jpg'
        )

        payload = {
            "airline_id": airline.id,
            "airline_name": airline.name,
            "boarding_deplaining_rating": 4,
            "crew_rating": 5,
            "services_rating": 3,
            "entertainment_rating": 4,
            "wi_fi_rating": 2,
        }

        res = self.client.post(AIRLINE_RATING_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airline_rating = AirlineRating.objects.get(id=res.data["id"])

        # Asserting the presence of corresponding fields
        for key in ("airline_id", "boarding_deplaining_rating", "crew_rating", "services_rating", "entertainment_rating",
                    "wi_fi_rating"):
            self.assertEqual(payload[key], getattr(airline_rating, key))
