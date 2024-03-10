from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from airport_system.models import (
    Airline, Flight, Airplane, AirplaneType, Airport, Route, Seat, AirlineRating, Country, City
)
from airport_system.serializers import AirlineListSerializer

AIRLINE_URL = reverse("airport_system:airline-list")
AIRLINE_RATING_URL = reverse("airport_system:airlinerating-list")
FLIGHT_URL = reverse("airport_system:flight-list")


def sample_airline(**kwargs):
    presets = {
        "name": "Test airline 1",
    }
    presets.update(kwargs)

    return Airline.objects.create(**presets)


def sample_flight(**kwargs):
    airplane_type = AirplaneType.objects.create(name="Test type")
    airline = kwargs.pop("airline")
    airplane = Airplane.objects.create(
        name="Azure", airline=airline, airplane_type=airplane_type
    )
    for seat_row in range(1, 21):
        for seat_number in range(1, 16):
            Seat.objects.create(
                airplane=airplane,
                row=seat_row,
                seat_number=seat_number
            )
    country_source = Country.objects.create(name="Country_1")
    closest_big_city_source = City.objects.create(name="City_1", country=country_source)
    source = Airport.objects.create(name="Source airport", iata_code="SAP", closest_big_city=closest_big_city_source)
    country_destination = Country.objects.create(name="Country_2")
    closest_big_city_destination = City.objects.create(name="City_2", country=country_destination)
    standard_destination = Airport.objects.create(
        name="Destination airport", iata_code="DAP", closest_big_city=closest_big_city_destination
    )
    route = Route.objects.create(
        source=source, standard_destination=standard_destination
    )

    initial_data = {
        "departure_time": "2023-02-16 14:00:00",
        "estimated_arrival_time": "2023-02-17 20:00:00",
        "airplane": airplane,
        "route": route,
    }
    initial_data.update(kwargs)

    return Flight.objects.create(**initial_data)


class UnauthenticatedAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com", "test password"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer ")

    def test_auth_required(self):
        res = self.client.get(AIRLINE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password",
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_airlines(self):
        sample_airline()
        sample_airline(name="Test airline 2")

        res = self.client.get(AIRLINE_URL)

        airlines = Airline.objects.order_by("id")
        serializer = AirlineListSerializer(airlines, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airline_forbidden(self):
        payload = {
            "name": "Airline",
        }
        res = self.client.post(AIRLINE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirlineApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com", "test password", is_staff=True
        )
        self.airline = sample_airline()
        self.flight = sample_flight(airline=self.airline)
        self.flight.save()
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_airline(self):
        payload = {
            "name": "Test airline 3",
            "headquarter": "New York City",
            "web_site_address": "http://www.testairline3.com",
            "iata_icao": "1234",
            "url_logo": "https://www.testairline3.com/logo1.jpg",
        }
        res = self.client.post(AIRLINE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airline = Airline.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(airline, key))

    def test_create_airline_rating(self):
        airline = Airline.objects.create(
            name="Test airline 4",
            headquarter='Philadelphia',
            web_site_address="http://www.testairline4.com",
            iata_icao='1234',
            url_logo="https://www.testairline3.com/logo1.jpg",
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

        for key in ("airline_id", "boarding_deplaining_rating", "crew_rating", "services_rating", "entertainment_rating",
                    "wi_fi_rating"):
            self.assertEqual(payload[key], getattr(airline_rating, key))

    def test_average_ratings_calculation(self):
        airline = Airline.objects.create(name="Test airline 5")

        AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=2,
            crew_rating=4,
            services_rating=3,
            entertainment_rating=5,
            wi_fi_rating=4
        )
        AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=3,
            crew_rating=5,
            services_rating=4,
            entertainment_rating=4,
            wi_fi_rating=1
        )

        new_rating = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=4,
            crew_rating=3,
            services_rating=2,
            entertainment_rating=3,
            wi_fi_rating=4
        )

        url = reverse("airport_system:airline-detail", kwargs={"pk": airline.id})
        res = self.client.get(url)
        data = res.json()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(data["avg_boarding_deplaining"], 3)
        self.assertEqual(data["avg_crew"], 4)
        self.assertEqual(data["avg_services"], 3)
        self.assertEqual(data["avg_entertainment"], 4)
        self.assertEqual(data["avg_wi_fi"], 3)

    def test_overall_rating_calculation(self):
        airline = Airline.objects.create(name="Test airline 6")

        rating_1 = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=2,
            crew_rating=4,
            services_rating=3,
            entertainment_rating=5,
            wi_fi_rating=3
        )

        rating_2 = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=5,
            crew_rating=4,
            services_rating=3,
            entertainment_rating=5,
            wi_fi_rating=5
        )

        url = reverse("airport_system:airline-detail", kwargs={"pk": airline.id})
        res = self.client.get(url)
        data = res.json()

        avg_boarding_deplaining = (rating_1.boarding_deplaining_rating + rating_2.boarding_deplaining_rating) / 2
        avg_crew = (rating_1.crew_rating + rating_2.crew_rating) / 2
        avg_services = (rating_1.services_rating + rating_2.services_rating) / 2
        avg_entertainment = (rating_1.entertainment_rating + rating_2.entertainment_rating) / 2
        avg_wi_fi = (rating_1.wi_fi_rating + rating_2.wi_fi_rating) / 2

        WEIGHTS = {
            "avg_boarding_deplaining": 0.05,
            "avg_crew": 0.2,
            "avg_services": 0.15,
            "avg_entertainment": 0.1,
            "avg_wi_fi": 0.05
        }

        expected_rating = (
            avg_boarding_deplaining * WEIGHTS["avg_boarding_deplaining"] +
            avg_crew * WEIGHTS["avg_crew"] +
            avg_services * WEIGHTS["avg_services"] +
            avg_entertainment * WEIGHTS["avg_entertainment"] +
            avg_wi_fi * WEIGHTS["avg_wi_fi"]
        ) / (WEIGHTS["avg_boarding_deplaining"] + WEIGHTS["avg_crew"] + WEIGHTS["avg_services"] + WEIGHTS["avg_entertainment"] + WEIGHTS["avg_wi_fi"])

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(data["overall_rating"], expected_rating)

    def test_ratings_update(self):
        airline = Airline.objects.create(name="Test airline 7")

        rating_1 = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=4,
            crew_rating=3,
            services_rating=5,
            entertainment_rating=2,
            wi_fi_rating=3
        )

        rating_2 = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=5,
            crew_rating=5,
            services_rating=4,
            entertainment_rating=4,
            wi_fi_rating=5
        )

        url = reverse("airport_system:airline-detail", kwargs={"pk": airline.id})
        response = self.client.get(url)
        data = response.json()

        avg_boarding_deplaining_old = data["avg_boarding_deplaining"]
        avg_crew_old = data["avg_crew"]
        avg_services_old = data["avg_services"]
        avg_entertainment_old = data["avg_entertainment"]
        avg_wi_fi_old = data["avg_wi_fi"]
        overall_rating_old = data["overall_rating"]

        new_rating = AirlineRating.objects.create(
            airline=airline,
            boarding_deplaining_rating=3,
            crew_rating=3,
            services_rating=2,
            entertainment_rating=4,
            wi_fi_rating=1
        )

        res = self.client.get(url)
        data = res.json()

        avg_boarding_deplaining_new = data["avg_boarding_deplaining"]
        avg_crew_new = data["avg_crew"]
        avg_services_new = data["avg_services"]
        avg_entertainment_new = data["avg_entertainment"]
        avg_wi_fi_new = data["avg_wi_fi"]
        overall_rating_new = data["overall_rating"]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotEqual(avg_boarding_deplaining_old, avg_boarding_deplaining_new)
        self.assertNotEqual(avg_crew_old, avg_crew_new)
        self.assertNotEqual(avg_services_old, avg_services_new)
        self.assertNotEqual(avg_entertainment_old, avg_entertainment_new)
        self.assertNotEqual(avg_wi_fi_old, avg_wi_fi_new)
        self.assertNotEqual(overall_rating_old, overall_rating_new)
