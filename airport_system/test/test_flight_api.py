from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from airport_system.models import (
    Flight, Airport, Route, Airline, Airplane, Crew, AirplaneType, Order, Ticket, Seat, City, Country
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
                    seat_number=seat_number,
                )
        cls.country_source = Country.objects.create(name="USA")
        cls.country_destination = Country.objects.create(name="Germany")
        cls.closest_big_city_source = City.objects.create(name="New York", country=cls.country_source)
        cls.closest_big_city_destination = City.objects.create(name="Berlin", country=cls.country_destination)
        cls.route_1 = Route.objects.create(
            source=Airport.objects.create(
                name="John F. Kennedy International Airport",
                iata_code="JFK",
                closest_big_city=cls.closest_big_city_source
            ),
            destination=Airport.objects.create(
                name="Berlin Tegel Airport 'Otto Lilienthal'",
                iata_code="TXL",
                closest_big_city=cls.closest_big_city_destination
            ),
            airline=cls.airline
        )
        cls.country_source = Country.objects.create(name="Portugal")
        cls.country_destination = Country.objects.create(name="Poland")
        cls.closest_big_city_source = City.objects.create(name="Lisbon", country=cls.country_source)
        cls.closest_big_city_destination = City.objects.create(name="Warsaw", country=cls.country_destination)
        cls.route_2 = Route.objects.create(
            source=Airport.objects.create(
                name="Humberto Delgado Airport",
                iata_code="LIS",
                closest_big_city=cls.closest_big_city_source
            ),
            destination=Airport.objects.create(
                name="Warsaw Chopin Airport",
                iata_code="WAW",
                closest_big_city=cls.closest_big_city_destination
            ),
            airline=cls.airline
        )
        # cls.crew = Crew.objects.create(first_name="John", last_name="Doe")

        cls.flight_1 = Flight.objects.create(
            airplane=cls.airplane,
            route=cls.route_1,
            departure_time="2022-06-02 14:00",
            estimated_arrival_time="2022-06-02 20:00",
            standard_airport=cls.route_1.source
        )
        # cls.flight_1.crew.add(cls.crew.id)
        print("Flight 1 created:")
        print("Flight ID:", cls.flight_1.id)
        print("Departure Time:", cls.flight_1.departure_time)
        print("Estimated Arrival Time:", cls.flight_1.estimated_arrival_time)
        print("standard airport:", cls.flight_1.standard_airport)

        cls.flight_1.save()

        cls.flight_2 = Flight.objects.create(
            airplane=cls.airplane,
            route=cls.route_2,
            departure_time="2022-07-04 22:00",
            estimated_arrival_time="2022-07-05 11:00",
            standard_airport=cls.route_2.source
        )
        # cls.flight_2.crew.add(cls.crew.id)
        cls.flight_2.save()


    def test_retrieve_flight_detail(self):
        a = self.flight_1
        print(f"HERE IS FLIGHT! {a}")
        b = self.route_1.source
        print(f"HERE IS ROUTE1 SOURCE! {b}")
        c = self.flight_1
        print(f"HERE IS ROUTE! {c.__dict__}")
        # Print the fields available in the Flight model
        print(f"Flight model fields: {Flight._meta.get_fields()}")
        url = detail_url(self.flight_1.id)
        print(f"URL for detail view: {url}")
        res = self.client.get(url)
        # print(f"Response status code: {res.status_code}")
        print(f"Response data: {res.data}")


        serializer = FlightDetailSerializer(self.flight_1)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        print(f"Response serializer: {serializer.data}")
        self.assertEqual(res.data, serializer.data)

    def test_list_flights(self):
        res = self.client.get(FLIGHT_URL)
        flights = Flight.objects.all()
        serializer = FlightListSerializer(flights, many=True)

        for flight, serialized_flight in zip(flights, serializer.data):
            # Вызываем метод tickets_available для каждого объекта Flight
            tickets_available = flight.tickets_available

            # Добавляем поле tickets_available в сериализованный вывод
            serialized_flight["tickets_available"] = tickets_available

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertListEqual(list(res.data), list(serializer.data))

    def test_filter_flights_by_source(self):
        aim_source = self.flight_1.route.source

        route = Route.objects.create(
            source=aim_source,
            destination=self.route_2.destination,
            airline=self.airline
        )

        Flight.objects.create(
            airplane=self.airplane,
            route=route,
            departure_time="2022-07-04 21:00",
            estimated_arrival_time="2022-07-05 12:00",
            standard_airport=route.source
        )

        res = self.client.get(
            FLIGHT_URL, {"airport_from": aim_source.name}
        )

        self.assertEqual(len(res.data), 2)
        for flight in res.data:
            a = flight["route_source"]
            print(f"SOURCE {a}")
            self.assertEqual(flight["route_source"], str(aim_source))

    def test_filter_flights_by_destination(self):
        aim_destination = self.flight_2.route.destination

        route = Route.objects.create(
            source=self.route_1.source,
            destination=aim_destination,
        )

        Flight.objects.create(
            airplane=self.airplane,
            route=route,
            departure_time="2022-07-04 21:00",
            estimated_arrival_time="2022-07-05 12:00",
            standard_airport=route.source
        )

        res = self.client.get(
            FLIGHT_URL, {"airport_to": aim_destination.name}
        )

        self.assertEqual(len(res.data), 2)
        for flight in res.data:
            self.assertEqual(flight["route_destination"], str(aim_destination))

    def test_tickets_available_if_several_tickets_ordered(self):
        user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        order = Order.objects.create(user=user) #added
        Ticket.objects.create(
            flight=self.flight_1,
            order=order,
            row=1,
            seat=1,
        )
        tickets_ordered = self.flight_1.tickets.count()
        res = self.client.get(FLIGHT_URL)

        tickets_available = self.flight_1.airplane.total_seats
        self.assertEqual(
            res.data[0]["tickets_available"],
            tickets_available - tickets_ordered
        )

    def test_tickets_available_if_all_tickets_ordered(self):
        user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        order = Order.objects.create(user=user)
        for seat_pair in self.flight_1.airplane.seats.all():
            Ticket.objects.create(
                flight=self.flight_1,
                order=order,
                row=seat_pair.row,
                seat=seat_pair.seat_number,
            )

        res = self.client.get(FLIGHT_URL)

        self.assertEqual(res.data[0]["tickets_available"], 0)
