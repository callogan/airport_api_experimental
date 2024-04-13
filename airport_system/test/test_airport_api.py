from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from airport_system.models import Airport, Country, City
from airport_system.serializers import AirportSerializer, AirportListSerializer

AIRPORT_URL = reverse("airport_system:airport-list")


def sample_airport(**kwargs):
    name = kwargs.get("name")
    iata_code = kwargs.get("iata_code")
    closest_big_city = kwargs.get("closest_big_city")

    defaults = {
        "name": name,
        "iata_code": iata_code,
        "closest_big_city": closest_big_city
    }
    defaults.update(kwargs)

    return Airport.objects.create(**defaults)


class UnauthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer ")

    def test_auth_required(self):
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password",
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_airports(self):
        # TEMPORARY CREATION MEAN
        # country_source_0 = Country.objects.create(name="USF")
        # closest_big_city = City.objects.create(name="New Jersey", country=country_source_0)
        # Airport.objects.create(name="Test_1", iata_code="TEZ", closest_big_city=closest_big_city)
        # MAIN CREATION MEAN
        country_source = Country.objects.create(name="USA")
        closest_big_city = City.objects.create(
            name="New York", country=country_source
        )
        sample_airport(
            name="John F. Kennedy International Airport", iata_code="JFK", closest_big_city=closest_big_city
        )
        # TEMPORARY CREATION MEAN
        # country_source = Country.objects.create(name="Country_21")
        # closest_big_city = City.objects.create(name="City_21", country=country_source)
        # Airport.objects.create(name="Test airport 2", iata_code="TEX", closest_big_city=closest_big_city)
        # MAIN CREATION MEAN
        country_source = Country.objects.create(name="Germany")
        closest_big_city = City.objects.create(
            name="Berlin", country=country_source
        )
        sample_airport(
            name="Berlin Tegel Airport 'Otto Lilienthal'", iata_code="TXL", closest_big_city=closest_big_city
        )

        res = self.client.get(AIRPORT_URL)
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!RESSSSSSSSSSSSSSSSS CONTENTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT {res.data}")

        airports = Airport.objects.order_by("id")
        serializer = AirportListSerializer(airports, many=True)
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!SER DATA {serializer.data}")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for res_data, serializer_data in zip(res.data, serializer.data):
            self.assertEqual(res_data["id"], serializer_data["id"])
            self.assertEqual(res_data["name"], serializer_data["name"])
            self.assertEqual(res_data["closest_big_city"], serializer_data["closest_big_city"])
            self.assertEqual(res_data["iata_code"], serializer_data["iata_code"])
            self.assertEqual(res_data["timezone"], serializer_data["timezone"])

    def test_create_airport_forbidden(self):
        payload = {
            "name": "Test airport",
            "iata_code": "XYZ",
            "closest_big_city": "Test city",
        }
        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com", "test password", is_staff=True
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_airport(self):
        country_source = Country.objects.create(name="Country_3")
        print(f"Создана страна: {country_source}")
        closest_big_city = City.objects.create(name="City_3", country=country_source)
        print(f"Создан город: {closest_big_city.country} в стране: {country_source}")
        payload = {
            "name": "Test airport 1",
            "iata_code": "XYZ",
            "closest_big_city": closest_big_city.id,
            'timezone': 'UTC'
        }
        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airport = Airport.objects.get(id=res.data["id"])
        print(f"CREATE AIRPORT {airport.__dict__}")

        # Вывести значения атрибутов аэропорта
        # print(f"Airport ID: {airport.id}")
        # print(f"Airport Name: {airport.name}")
        # print(f"Airport IATA Code: {airport.iata_code}")
        # print(f"Airport Closest Big City: {airport.closest_big_city}")
        self.assertEqual(payload["name"], airport.name)
        self.assertEqual(payload["closest_big_city"], airport.closest_big_city.id)
        self.assertEqual(payload["iata_code"], airport.iata_code)
        self.assertEqual(payload["timezone"], airport.timezone)
        # ISSUE WITH COMPARISON
        # self.assertEqual(payload["id"], airport.id)
