from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from airport_system.models import (
    Flight,
    Airport,
    Route,
    Airline,
    Airplane,
    Crew,
    AirplaneType,
    Order,
    Ticket,
    Seat,
    City,
    Country,
)
from airport_system.serializers import FlightDetailSerializer, FlightListSerializer

FLIGHT_URL = reverse("airport_system:flight-list")


def detail_url(flight_id):
    return reverse("airport_system:flight-detail", args=[flight_id])


class UnauthenticatedFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @classmethod
    def setUpTestData(cls):
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
                    seat_number=seat_number
                )
        cls.country_source = Country.objects.create(name="USA")
        cls.country_destination = Country.objects.create(name="Germany")
        cls.closest_big_city_source = City.objects.create(
            name="New York", country=cls.country_source
        )
        cls.closest_big_city_destination = City.objects.create(
            name="Berlin", country=cls.country_destination
        )
        cls.route_1 = Route.objects.create(
            source=Airport.objects.create(
                name="John F. Kennedy International Airport",
                iata_code="JFK",
                closest_big_city=cls.closest_big_city_source
            ),
            standard_destination=Airport.objects.create(
                name="Berlin Tegel Airport 'Otto Lilienthal'",
                iata_code="TXL",
                closest_big_city=cls.closest_big_city_destination,
            ),
            airline=cls.airline
        )
        cls.country_source = Country.objects.create(name="Portugal")
        cls.country_destination = Country.objects.create(name="Poland")
        cls.closest_big_city_source = City.objects.create(
            name="Lisbon", country=cls.country_source
        )
        cls.closest_big_city_destination = City.objects.create(
            name="Warsaw", country=cls.country_destination
        )
        cls.route_2 = Route.objects.create(
            source=Airport.objects.create(
                name="Humberto Delgado Airport",
                iata_code="LIS",
                closest_big_city=cls.closest_big_city_source
            ),
            standard_destination=Airport.objects.create(
                name="Warsaw Chopin Airport",
                iata_code="WAW",
                closest_big_city=cls.closest_big_city_destination,
            ),
            airline=cls.airline
        )
        cls.crew = Crew.objects.create(first_name="Julie", last_name="Harrington")

        cls.flight_1 = Flight.objects.create(
            airplane=cls.airplane,
            route=cls.route_1,
            departure_time="2022-06-02 14:00",
            estimated_arrival_time="2022-06-02 20:00"
        )
        cls.flight_1.crew.add(cls.crew.id)

        cls.flight_1.save()

        cls.flight_2 = Flight.objects.create(
            airplane=cls.airplane,
            route=cls.route_2,
            departure_time="2022-07-04 22:00",
            estimated_arrival_time="2022-07-05 11:00"
        )
        cls.flight_2.crew.add(cls.crew.id)
        cls.flight_2.save()

    def test_retrieve_flight_detail(self):
        url = detail_url(self.flight_1.id)
        res = self.client.get(url)

        res.data["departure_time"] = datetime.strptime(
            res.data["departure_time"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%Y-%m-%d %H:%M")

        res.data["estimated_arrival_time"] = datetime.strptime(
            res.data["estimated_arrival_time"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%Y-%m-%d %H:%M")

        serializer = FlightDetailSerializer(self.flight_1)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        for key in res.data:
            if key != "airplane":
                self.assertEqual(res.data[key], serializer.data[key])
            else:
                self.assertListEqual(list(res.data[key]), list(serializer.data[key]))

    def test_list_flights(self):
        res = self.client.get(FLIGHT_URL)
        flights = Flight.objects.all()
        serializer = FlightListSerializer(flights, many=True)

        for flight, serialized_flight in zip(flights, serializer.data):
            tickets_available = flight.tickets_available

            serialized_flight["tickets_available"] = tickets_available

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertListEqual(list(res.data), list(serializer.data))

    def test_filter_flights_by_source_exist(self):
        aim_source = self.flight_1.route.source

        route = Route.objects.create(
            source=aim_source,
            standard_destination=self.route_2.standard_destination,
            airline=self.airline
        )

        Flight.objects.create(
            airplane=self.airplane,
            route=route,
            departure_time="2022-07-04 21:00",
            estimated_arrival_time="2022-07-05 12:00"
        )

        res = self.client.get(FLIGHT_URL, {"airport_from": aim_source.name})

        self.assertEqual(len(res.data), 2)
        for flight in res.data:
            self.assertEqual(flight["route_source"], str(aim_source))

    def test_filter_flights_by_source_absent(self):
        aim_source_name = "San Francisco International Airport"

        res = self.client.get(FLIGHT_URL, {"airport_from": aim_source_name})

        self.assertEqual(len(res.data), 0)

    def test_filter_flights_by_destination_exist(self):
        aim_destination = self.flight_2.route.standard_destination

        route = Route.objects.create(
            source=self.route_1.source,
            standard_destination=aim_destination,
        )

        Flight.objects.create(
            airplane=self.airplane,
            route=route,
            departure_time="2022-07-04 21:00",
            estimated_arrival_time="2022-07-05 12:00"
        )

        res = self.client.get(FLIGHT_URL, {"airport_to": aim_destination.name})

        self.assertEqual(len(res.data), 2)
        for flight in res.data:
            self.assertEqual(flight["route_standard_destination"], str(aim_destination))

    def test_filter_flights_by_destination_absent(self):
        aim_destination_name = "Ministro Pistarini International Airport"

        res = self.client.get(FLIGHT_URL, {"airport_to": aim_destination_name})

        self.assertEqual(len(res.data), 0)

    def test_tickets_available_if_several_tickets_ordered(self):
        # CONSIDER DO YOU REALLY NEED THIS USER OR JUST TAKE USER FROM SET UP FILE - self.user
        user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password"
        )
        order = Order.objects.create(user=user)
        Ticket.objects.create(
            flight=self.flight_1,
            order=order,
            row=1,
            seat=1
        )
        tickets_ordered = self.flight_1.tickets.count()
        res = self.client.get(FLIGHT_URL)

        tickets_available = self.flight_1.airplane.total_seats
        self.assertEqual(
            res.data[0]["tickets_available"], tickets_available - tickets_ordered
        )

    def test_tickets_available_if_all_tickets_ordered(self):
        user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password"
        )
        order = Order.objects.create(user=user)
        for seat_pair in self.flight_1.airplane.seats.all():
            Ticket.objects.create(
                flight=self.flight_1,
                order=order,
                row=seat_pair.row,
                seat=seat_pair.seat_number
            )

        res = self.client.get(FLIGHT_URL)

        self.assertEqual(res.data[0]["tickets_available"], 0)

    def test_create_flight_by_not_admin_is_forbidden(self):
        payload = {
            "airplane": self.airplane.id,
            "route": self.route_1.id,
            "departure_time": "2022-07-04 21:00",
            "estimated_arrival_time": "2022-07-05 12:00"
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test password"
        )
        self.client.force_authenticate(self.user)

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminFlightApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com", "test password", is_staff=True
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    @classmethod
    def setUpTestData(cls):
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
        cls.country_source = Country.objects.create(name="USA")
        cls.country_destination = Country.objects.create(name="Germany")
        cls.closest_big_city_source = City.objects.create(
            name="New York", country=cls.country_source
        )
        cls.closest_big_city_destination = City.objects.create(
            name="Berlin", country=cls.country_destination
        )
        cls.route = Route.objects.create(
            source=Airport.objects.create(
                name="John F. Kennedy International Airport",
                iata_code="JFK",
                closest_big_city=cls.closest_big_city_source
            ),
            standard_destination=Airport.objects.create(
                name="Berlin Tegel Airport 'Otto Lilienthal'",
                iata_code="TXL",
                closest_big_city=cls.closest_big_city_destination
            ),
            airline=cls.airline,
        )
        cls.crew = Crew.objects.create(first_name="Julie", last_name="Harrington")
        cls.source = cls.route.source

    def test_create_flight(self):
        payload = {
            "airplane": self.airplane.id,
            "route": self.route.id,
            "departure_time": "2022-07-04 21:00",
            "estimated_arrival_time": "2022-07-05 12:00",
            "crew": [self.crew.id],
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        flight = Flight.objects.get(id=res.data["id"])
        for key in ("airplane", "route"):
            self.assertEqual(payload[key], getattr(flight, key).id)
        for key in ("departure_time", "estimated_arrival_time"):
            self.assertEqual(
                payload[key], getattr(flight, key).strftime("%Y-%m-%d %H:%M")
            )

    def test_update_flight(self):
        flight = Flight.objects.create(
            airplane=self.airplane,
            route=self.route,
            departure_time=datetime(2024, 1, 10, 12, 30, 0),
            estimated_arrival_time=datetime(2024, 1, 10, 14, 30, 0)
        )
        flight.crew.add(self.crew.id)
        flight.save()

        country_source = Country.objects.create(name="Emergent_country")
        closest_big_city_source = City.objects.create(name="Emergent_city", country=country_source)
        self.route.emergent_destination = Airport.objects.create(
            name="Updated emergent airport",
            iata_code="UPD",
            closest_big_city=closest_big_city_source
        )
        self.route.save()

        payload = {
            "real_arrival_time": datetime(2024, 1, 10, 16, 00, 0),
            "route": self.route.id
        }

        res = self.client.patch(detail_url(flight.id), data=payload, format='json')
        flight.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(
            payload["real_arrival_time"].strftime('%Y-%m-%d %H:%M'),
            flight.real_arrival_time.strftime('%Y-%m-%d %H:%M')
        )

        self.assertEqual(payload["route"], flight.route.id)
