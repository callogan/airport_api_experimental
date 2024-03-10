import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from airport_system.models import (
    Airplane,
    AirplaneType,
    Seat,
    Airline,
    Country,
    City,
    Airport,
    Route,
    Flight,
    airplane_image_file_path
)
from airport_system.serializers import AirplaneListSerializer

AIRPLANE_URL = reverse("airport_system:airplane-list")


def image_upload_url(airplane_id):
    return reverse("airport_system:airplane-upload-image", args=[airplane_id])


def sample_airline(**kwargs):
    defaults = {
        "name": "Test airline 1",
    }
    defaults.update(kwargs)

    return Airline.objects.create(**defaults)


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
                seat_number=seat_number,
            )

    country_source = Country.objects.create(name="Country_1")
    closest_big_city_source = City.objects.create(name="City_1", country=country_source)
    source = Airport.objects.create(name="Source airport", iata_code="WAV", closest_big_city=closest_big_city_source)
    country_destination = Country.objects.create(name="Country_2")
    closest_big_city_destination = City.objects.create(name="City_2", country=country_destination)
    standard_destination = Airport.objects.create(
        name="Destination airport", iata_code="DAP", closest_big_city=closest_big_city_destination
    )
    route = Route.objects.create(
        source=source, standard_destination=standard_destination
    )

    presets = {
        "departure_time": "2023-02-16 14:00:00",
        "estimated_arrival_time": "2023-02-17 20:00:00",
        "airplane": airplane,
        "route": route,
    }
    presets.update(kwargs)

    return Flight.objects.create(**presets)


def sample_airplane_standard(**kwargs):
    airline = Airline.objects.create(name="Test airline 2")
    airplane_type = AirplaneType.objects.create(
        name="Test type 1"
    )

    presets = {
        "name": "Test standard name",
        "airplane_type": airplane_type,
        "airline": airline
    }
    presets.update(kwargs)

    airplane = Airplane.objects.create(
        name="Beige", airline=airline, airplane_type=airplane_type
    )

    for seat_row in range(1, 21):
        for seat_number in range(1, 16):
            Seat.objects.create(
                airplane=airplane,
                row=seat_row,
                seat_number=seat_number
            )

    return airplane


def sample_airplane_custom(**kwargs):
    airline = Airline.objects.create(name="Test airline 3")
    airplane_type = AirplaneType.objects.create(
        name="Test type"
    )

    presets = {
        "name": "Test custom name",
        "airplane_type": airplane_type,
        "airline": airline
    }
    presets.update(kwargs)

    airplane = Airplane.objects.create(
        name="Crimson", airline=airline, airplane_type=airplane_type
    )

    for seat_row in range(1, 21):
        num_seat_numbers = seat_row % 5 + 1
        seat_numbers = range(1, num_seat_numbers + 1)

        for seat_number in seat_numbers:
            Seat.objects.create(
                airplane=airplane,
                row=seat_row,
                seat_number=seat_number
            )

    return airplane


class UnauthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com", "test password"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer ")

    def test_auth_required(self):
        res = self.client.get(AIRPLANE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedAirportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password"
        )

        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_airplanes(self):
        sample_airplane_standard()

        airplane_type = AirplaneType.objects.create(
            name="Test type 2"
        )
        airline = Airline.objects.create(name="Test airline")

        data = {
            "name": "Test name 2",
            "airplane_type": airplane_type,
            "airline": airline
        }
        airplane = Airplane.objects.create(**data)

        for seat_row in range(1, 21):
            num_seat_numbers = seat_row % 5 + 1
            seat_numbers = range(1, num_seat_numbers + 1)

            for seat_number in seat_numbers:
                Seat.objects.create(
                    airplane=airplane,
                    row=seat_row,
                    seat_number=seat_number
                )

        res = self.client.get(AIRPLANE_URL)

        airplanes = Airplane.objects.order_by("id")
        serializer = AirplaneListSerializer(airplanes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for res_data, serializer_data in zip(res.data, serializer.data):
            self.assertEqual(res_data["id"], serializer_data["id"])
            self.assertEqual(res_data["name"], serializer_data["name"])
            self.assertEqual(res_data['airplane_type'], serializer_data['airplane_type'])
            self.assertEqual(res_data["total_seats"], serializer_data["total_seats"])
            self.assertEqual(res_data["total_rows"], serializer_data["total_rows"])
            self.assertListEqual(list(res_data["rows_with_seat_count"]), list(serializer_data["rows_with_seat_count"]))
            self.assertEqual(res_data["image"], serializer_data["image"])

    def test_create_airplane_forbidden(self):
        airline = Airline.objects.create(name="Test airline")
        airplane_type = AirplaneType.objects.create(
            name="Test type"
        )

        payload = {
            "name": "Test standard name",
            "airplane_type": airplane_type.id,
            "airline": airline.id,
            "total_rows": 40,
            "total_seats": 200
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
            is_staff=True
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_airplane(self):
        airline = Airline.objects.create(name="Test airline")
        airplane_type = AirplaneType.objects.create(
            name="Test type"
        )
        payload = {
            "name": "Boeing 737",
            "airline": airline.id,
            "airplane_type": airplane_type.id,
            "total_rows": 40,
            "total_seats": 200
        }
        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        airplane = Airplane.objects.get(id=res.data["id"])
        self.assertEqual(payload["name"], airplane.name)
        self.assertEqual(payload["total_rows"], airplane.total_rows)
        self.assertEqual(payload["total_seats"], airplane.total_seats)
        self.assertEqual(payload["airline"], airplane.airline.id)
        self.assertEqual(payload["airplane_type"], airplane.airplane_type.id)


class AirplaneImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.airplane = sample_airplane_standard()
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_upload_image_to_airplane(self):
        url = image_upload_url(self.airplane.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.airplane.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)

        uploaded_image = self.airplane.image
        self.assertTrue(uploaded_image.file)

    def test_airplane_image_file_path(self):
        filename = "test_image.jpg"
        result_path = airplane_image_file_path(self.airplane, filename)

        self.assertTrue(slugify(self.airplane.name) in result_path)

        uuid_part = result_path.split(slugify(self.airplane.name))[1].split(".jpg")[0]

        self.assertEqual(len(uuid_part), 37)
        self.assertTrue(all(c.isdigit() or c.isalpha() or c in "-_" for c in uuid_part))
        self.assertTrue(slugify(self.airplane.name) in result_path)
