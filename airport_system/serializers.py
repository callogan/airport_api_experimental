import pytz
import validators as validators
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.validators import UniqueTogetherValidator

from .models import (
    Country,
    City,
    Airport,
    Seat,
    AirplaneType,
    Airplane,
    Airline,
    Route,
    Flight,
    Order,
    Ticket, Seat, AirlineRating,
)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name")


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "country")


class CityListSerializer(CitySerializer):
    country = serializers.SlugRelatedField(slug_field="name", read_only=True)


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city", "iata_code", "timezone")


class AirportListSerializer(AirportSerializer):
    closest_big_city = serializers.SlugRelatedField(slug_field="name", read_only=True)


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(slug_field="name", read_only=True)
    destination = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "destination")


class RouteDetailSerializer(serializers.ModelSerializer):
    source = AirportSerializer(read_only=True)
    destination = AirportSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
    total_rows = serializers.SerializerMethodField()
    rows_with_seat_count = serializers.SerializerMethodField()

    def get_total_rows(self, obj):
        # Return the value of the property from the model instance
        # print(f"Содержимое объекта obj: {obj}")
        return obj.total_rows

    def get_rows_with_seat_count(self, obj):
        # Return the value of the property from the model instance
        # print(f"Содержимое объекта obj: {obj} два")
        return obj.rows_with_seat_count()

    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "airplane_type",
            "capacity",
            "total_rows",
            "rows_with_seat_count",
            "image",
        )

    # optional_field = serializers.CharField(required=False)

class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(slug_field="name", read_only=True)


class AirplaneCreateSerializer(serializers.ModelSerializer):
    total_rows = serializers.IntegerField(required=False)
    total_seats = serializers.IntegerField(required=False)
    rows = serializers.ListField(child=serializers.IntegerField(), required=False)
    row_seats_distribution = serializers.ListField(child=serializers.IntegerField(), required=False)

    class Meta:
        model = Airplane
        fields = ['name', 'airline', 'airplane_type', "total_rows",  "total_seats", "rows", "row_seats_distribution"]

    def validate(self, attrs):
        print(attrs)
        data = super(AirplaneCreateSerializer, self).validate(attrs=attrs)
        total_rows = attrs["total_rows"]
        total_seats = attrs["total_seats"]

        Airplane.validate_airplane(
            total_rows,
            total_seats,
            ValidationError
        )

        return data

    def create(self, validated_data):
        total_rows = validated_data.pop('total_rows', None)
        total_seats = validated_data.pop('total_seats', None)
        rows = validated_data.pop('rows', None)
        row_seats_distribution = validated_data.pop('row_seats_distribution', None)

        airplane_instance = super().create(validated_data)

        if total_rows and total_seats:
            self._create_standard_airplane(airplane_instance, total_rows, total_seats)
        elif rows and row_seats_distribution:
            self._create_custom_airplane(airplane_instance, rows, row_seats_distribution)
        else:
            raise ValidationError('No seats data provided')

        return airplane_instance

    def _create_standard_airplane(self, airplane, total_rows, total_seats):

        seats_per_row = total_seats // total_rows
        for row in range(1, total_rows + 1):
            for seat_num in range(1, seats_per_row + 1):
                Seat.objects.create(
                    airplane=airplane,
                    row=row,
                    seat_number=seat_num
                )

        # создание самолета с одинаковыми рядами

    def _create_custom_airplane(self, airplane, rows, row_seats_distribution):

        for row, seats in zip(rows, row_seats_distribution):
            for seat_num in range(1, seats + 1):
                Seat.objects.create(
                    airplane=airplane,
                    row=row,
                    seat_number=seat_num
                )
    #
    # def calculate_seats_per_row(self, airplane, total_rows):
    #     total_seats = Seat.objects.filter(airplane=airplane).count()
    #     return total_seats // total_rows



class AirlineSerializer(serializers.ModelSerializer):
    airplanes = AirplaneSerializer(many=True, read_only=False, allow_null=False)

    overall_rating = serializers.SerializerMethodField()

    avg_boarding_deplaining = serializers.SerializerMethodField(read_only=True)
    avg_crew = serializers.SerializerMethodField(read_only=True)
    avg_service = serializers.SerializerMethodField(read_only=True)
    avg_entertainment = serializers.SerializerMethodField(read_only=True)
    avg_wi_fi = serializers.SerializerMethodField(read_only=True)

    def get_overall_rating(self, obj):
        return obj.overall_rating['overall_rating']

    def get_avg_boarding_deplaining(self, obj):
        return obj.overall_rating['avg_boarding_deplaining']

    def get_avg_crew(self, obj):
        return obj.overall_rating['avg_crew']

    def get_avg_service(self, obj):
        return obj.overall_rating['avg_service']

    def get_avg_entertainment(self, obj):
        return obj.overall_rating['avg_entertainment']

    def get_avg_wi_fi(self, obj):
        return obj.overall_rating['avg_wi_fi']

    def create(self, validated_data):
        airplanes_data = validated_data.pop('airplanes')
        airline = Airline.objects.create(**validated_data)
        for airplane_data in airplanes_data:
            Airplane.objects.create(airline=airline, **airplane_data)
        return airline

    #RATING LOGIC
    # def update(self, instance, validated_data):
    #     print("Validated data received in update:", validated_data)
    #     # Логика обновления рейтинга
    #     if 'rating' in validated_data:
    #         rating_data = validated_data.pop('rating')
    #         print("Rating data received in update:", rating_data)
    #         self.update_rating(instance, rating_data)
    #
    #     # Логика обновления списка самолетов
    #     if 'airplanes' in validated_data:
    #         airplanes_data = validated_data.pop('airplanes')
    #         self.update_airplanes(instance, airplanes_data)
    #
    #     instance.save()
    #     return instance
    #
    # def update_rating(self, airline, validated_data):
    #
    #     rating, created = AirlineRating.objects.get_or_create(
    #         airline=airline
    #     )
    #
    #     boarding_deplaining_rating = validated_data.pop('boarding_deplaining_rating', None)
    #     if boarding_deplaining_rating:
    #         rating.boarding_deplaining_rating = boarding_deplaining_rating
    #
    #     crew_rating = validated_data.pop('crew_rating', None)
    #     if crew_rating:
    #         rating.crew_rating = crew_rating
    #
    #     services_rating = validated_data.pop('services_rating', None)
    #     if services_rating:
    #         rating.services_rating = services_rating
    #
    #     entertainment_rating = validated_data.pop('entertainment_rating', None)
    #     if entertainment_rating:
    #         rating.entertainment_rating = entertainment_rating
    #
    #     wi_fi_rating = validated_data.pop('wi_fi_rating', None)
    #     if wi_fi_rating:
    #         rating.wi_fi_rating = wi_fi_rating
    #
    #     rating.save()
    #
    #     print("Rating updated successfully")
    #     return rating

    # def update_rating(self, instance, validated_data):
    #     # print("Data received in update_rating:", validated_data)
    #     # print("Data received in update_rating:", validated_data)
    #     # логика расчета overall_rating
    #     # Извлечение значений из JSON-данных
    #     boarding_deplaining_rating = validated_data.pop('boarding_deplaining_rating')
    #     crew_rating = validated_data.pop('crew_rating')
    #     services_rating = validated_data.pop('services_rating')
    #     entertainment_rating = validated_data.pop('entertainment_rating')
    #     wi_fi_rating = validated_data.pop('wi_fi_rating')
    #
    #     # Обновление полей модели
    #     instance.boarding_deplaining_rating = boarding_deplaining_rating
    #     instance.crew_rating = crew_rating
    #     instance.services_rating = services_rating
    #     instance.entertainment_rating = entertainment_rating
    #     instance.wi_fi_rating = wi_fi_rating
    #     instance.save()
    #     print("Rating updated successfully")
    #     return instance

    def update_airplanes(self, instance, airplanes_data):
        instance.airplanes.all().delete()
        for airplane_data in airplanes_data:
            Airplane.objects.create(airline=instance, **airplane_data)
        return instance

    # def save(self, **kwargs):
    #     # Обработка сохранения объекта Airline
    #     super().save(**kwargs)
    #
    #     # Обновление рейтинга
    #     if 'rating' in self.validated_data:
    #         self.update_rating(self.instance, self.validated_data['rating'])
    #
    #     # Обновление списка самолетов
    #     if 'airplanes' in self.validated_data:
    #         self.update_airplanes(self.instance, self.validated_data['airplanes'])

    class Meta:
        model = Airline
        fields = (
            "id",
            "name",
            "headquarter",
            "web_site_address",
            "iata_icao",
            "url_logo",
            "airplanes",
            "overall_rating",
            'avg_boarding_deplaining',
            'avg_crew',
            'avg_service',
            'avg_entertainment',
            'avg_wi_fi',
            'ratings'
        )


class AirlineListSerializer(AirlineSerializer):
    class Meta:
        model = Airline
        fields = ("id", "name", "headquarter", "iata_icao")


class RatingSerializer(serializers.ModelSerializer):
    # def create(self, validated_data):
    #     a = validated_data
    #     print("Data received in create method:", a)
    #     ratings_data = validated_data.pop('ratings')
    #     rating = AirlineRating.objects.create(**validated_data)
    # #     for rating_data in ratings_data:
    # #         Airplane.objects.create(airline=airline, **airplane_data)
    # #     return airline

    airline_name = serializers.SlugRelatedField(
        slug_field='name', queryset=Airline.objects.all(), source='airline'
    )

    def create(self, validated_data):
        ratings_data = validated_data.pop('ratings', [])
        rating = AirlineRating.objects.create(**validated_data)

        for rating_data in ratings_data:
            AirlineRating.objects.create(parent=rating, **rating_data)
        return rating

    class Meta:
        model = AirlineRating
        fields = (
            'id',
            'airline_name',
            'boarding_deplaining_rating',
            'crew_rating',
            'services_rating',
            'entertainment_rating',
            'wi_fi_rating'
        )


class AirplaneImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ("id", "image")


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = '__all__'


class FlightListSerializer(FlightSerializer, serializers.ModelSerializer):
    route = serializers.CharField(source="route.__str__", read_only=True)
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)
    airplane_capacity = serializers.IntegerField(
        source="airplane.capacity", read_only=True
    )
    # tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane_name",
            "airplane_capacity",
            # "tickets_available",
            "departure_time",
            "arrival_time",
        )


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        row = attrs["row"]
        seat = attrs["seat"]
        flight = attrs["flight"]

        Ticket.validate_ticket(
            row,
            seat,
            flight,
            ValidationError
        )

        return data

    queryset = Ticket.objects.all()

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight", "type", "allocated")


class TicketListSerializer(TicketSerializer):
    flight = FlightListSerializer(many=False, read_only=True)


class TicketSeatsSerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = ("row", "seat")


class FlightDetailSerializer(serializers.ModelSerializer):
    route = RouteDetailSerializer(read_only=True)
    airplane = AirplaneSerializer(read_only=True)
    taken_places = TicketSeatsSerializer(source="tickets", many=True, read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane",
            "departure_time",
            "arrival_time",
            "taken_places",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_null=False)

    tickets_available = serializers.SerializerMethodField()

    def get_tickets_available(self, obj):
        # Return the value of the property from the model instance
        return obj.tickets_available

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at", 'tickets_available')

    # NEW CREATION (with special allocation)
    def create(self, validated_data):
        with transaction.atomic():
            b = validated_data
            print(b)
            tickets_data = validated_data.pop("tickets")
            print(tickets_data)
            # Get flight instance
            flight = tickets_data[0]['flight']

            # tickets = Ticket.objects.filter(flight_id=flight.id)
            ticket = Ticket.objects.filter(flight=flight).first()


            # Get number of tickets available
            # tickets_available = Ticket.objects.filter(sold=False).count()
            # order_instance = super().create(validated_data)
            # print(order_instance)
            # # Извлечение flight из первого билета в tickets
            # if order_instance.tickets.exists():  # Проверка наличия билетов
            #     print("I am in")
            #     first_ticket = order_instance.tickets.first()
            #     flight = first_ticket.flight

                # Извлечение tickets_available из flight
            tickets_available = ticket.order.tickets_available

            if tickets_available < len(tickets_data):
                raise serializers.ValidationError("Not enough tickets available")

            order = Order.objects.create(**validated_data)

            for ticket_data in tickets_data:
                print('Ticket Data:', ticket_data)
                if ticket_data["type"] == "check-in-pending":
                    ticket = Ticket.objects.create(order=order, **ticket_data)
                    print(f'Ticket created - Type: {ticket.type}, Seat: {ticket.seat}, Row: {ticket.row}')
                    # ticket.allocate_seat()
                else:
                    Ticket.objects.create(order=order, **ticket_data)

            return order

    #OLD CREATION (just simple booking)
    # def create(self, validated_data):
    #     with transaction.atomic():
    #         tickets_data = validated_data.pop("tickets")
    #         order = Order.objects.create(**validated_data)
    #         for ticket_data in tickets_data:
    #             Ticket.objects.create(order=order, **ticket_data)
    #         return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
