import pytz
import validators as validators
from django.db import transaction
from rest_framework import serializers, status
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
    Airlines,
    Route,
    Flight,
    Order,
    Ticket, Seat,
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
        return obj.total_rows

    def get_rows_with_seat_count(self, obj):
        # Return the value of the property from the model instance
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


class StandardSeatsField(serializers.Field):
    def to_representation(self, seats):
        return {
            "rows": seats.row,
            "seats": seats.seat_number
        }

    def to_internal_value(self, data):
        return Seat(rows=data['rows'], seats=data['seats'])


class CustomSeatsField(serializers.Field):
    def to_representation(self, seats):
        return [item['seat_number'] for item in seats]


class AirplaneCreateSerializer(serializers.ModelSerializer):
    # seats = SeatSerializer(many=True, read_only=False)

    seats = StandardSeatsField(source='*', required=False)
    custom_seats = CustomSeatsField(source='*', required=False)

    class Meta:
        model = Airplane
        fields = ['name', 'airline', 'seats', 'custom_seats']

    def validate(self, data):
        # валидация данных
        return data

    def get_rows_with_seat_count(self, obj):
        # Return the value of the property from the model instance
        return obj.rows_with_seat_count()

    def create(self, validated_data):
        seats_data = validated_data.get('seats')
        custom_seats_data = validated_data.get('custom_seats')

        if seats_data:
            airplane = self._create_standard_airplane(seats_data)
        elif custom_seats_data:
            airplane = self._create_custom_airplane(custom_seats_data)
        else:
            raise ValidationError('No seats data provided')

        return airplane

    def _create_standard_airplane(self, airplane, total_rows, obj):
        seats_per_row = self.get_rows_with_seat_count(obj)
        for row in range(1, total_rows + 1):
            for seat_number in range(1, seats_per_row + 1):
                Seat.objects.create(airplane=airplane, row=row, seat_number=seat_number)

        # создание самолета с одинаковыми рядами

    def _create_custom_airplane(self, airplane, custom_seats_data):

    # создание самолета с разными рядами

        for row_data in custom_seats_data:
            row = row_data['seats__row']
            count = row_data['seat_count']

            for seat_num in range(1, count + 1):
                Seat.objects.create(
                    airplane=airplane,
                    row=row,
                    seat_number=seat_num
                )
    #
    # def calculate_seats_per_row(self, airplane, total_rows):
    #     total_seats = Seat.objects.filter(airplane=airplane).count()
    #     return total_seats // total_rows


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(slug_field="name", read_only=True)


class AirlinesSerializer(serializers.ModelSerializer):
    airplanes = AirplaneSerializer(many=True, read_only=False, allow_null=False)

    #RATING LOGIC
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Создание авиалинии
        self.perform_create(serializer)

        # Создание оценки для авиалинии
        airline = serializer.instance
        evaluation_data = {'airlines': airline.id, 'score': request.data.get('score')}
        evaluation_serializer = AirlineEvaluationSerializer(data=evaluation_data)
        evaluation_serializer.is_valid(raise_exception=True)
        evaluation_serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    class Meta:
        model = Airlines
        fields = ("id", "name", "headquarter", "web_site_address", "iata_icao", "url_logo", "airplanes")


class AirlinesListSerializer(AirlinesSerializer):
    class Meta:
        model = Airlines
        fields = ("id", "name", "headquarter", "iata_icao")


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
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "route",
            "airplane_name",
            "airplane_capacity",
            "tickets_available",
            "departure_time",
            "arrival_time",
        )

    def get_tickets_available(self, flight):
        # Calculate the available tickets using the provided formula
        total_seats = flight.airplane.rows * flight.airplane.seats_in_row
        sold_tickets = flight.tickets.count()
        available_tickets = max(0, total_seats - sold_tickets)
        return available_tickets


class TicketSerializer(serializers.ModelSerializer):
    # def validate(self, attrs):
    #     data = super(TicketSerializer, self).validate(attrs=attrs)
    #     Ticket.validate_ticket(
    #         attrs["row"], attrs["seat"], attrs["flight"].airplane, ValidationError
    #     )
    #     return data

    # # NEW_VALIDATOR
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight", "type")

        validators = [
            UniqueTogetherValidator(
                queryset=Ticket.objects.all(),
                fields=["flight", "row", "seat"],
                message="Ticket with this combination of flight, row, and seat already exists."
            )
        ]

    def validate(self, data):
        airplane = data['flight'].airplane
        row_value = data['row']
        seat_value = data['seat']

        # Используем метод get_rows_info() для получения информации о рядах
        rows_info = airplane.rows_with_seat_count()

        # Дополнительная валидация, например, проверка на диапазон мест
        self.context['request'] = self.context.get('request', self.context.get('view', None))
        error_to_raise = ValidationError

        # Custom validation for seat within the valid range for the given row
        valid_seat_range = rows_info.get(row_value, {}).get("valid_seat_range", {})
        if not (valid_seat_range.get("min", 1) <= seat_value <= valid_seat_range.get("max", float('inf'))):
            raise error_to_raise({
                "seat": f"Seat {seat_value} is not valid for the given row."
            })

        # Call the validate_ticket method
        airplane.validate_ticket(row=row_value, seat=seat_value, flight=data['flight'], error_to_raise=error_to_raise)

        # Additional validation specific to your serializer
        # ...

        return data


    # EXISTING_VALIDATOR
    # class Meta:
    #     model = Ticket
    #     fields = ("id", "row", "seat", "flight")
    #     validators = [
    #         UniqueTogetherValidator(
    #             queryset=Ticket.objects.all(),
    #             fields=["flight", "row", "seat"],
    #             message="validation_error"
    #         )
    #     ]


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

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    # NEW CREATION (with special allocation)
    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                if ticket_data["type"] == "check-in-pending":
                    ticket = Ticket.objects.create(order=order, **ticket_data)
                    ticket.allocate_seat() # what should I give as a parameter
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
