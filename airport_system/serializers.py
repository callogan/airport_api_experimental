from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer, OpenApiExample
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


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
    Ticket, Seat, AirlineRating, Crew,
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
    # closest_big_city = serializers.CharField(max_length=255)

    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city", "iata_code", "timezone")


class AirportListSerializer(AirportSerializer):
    closest_big_city = serializers.SlugRelatedField(slug_field="name", read_only=True)


class RouteSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data.get('status') is 'emergency' and data.get('emergent_destination') is None:
            raise serializers.ValidationError("Must update emergent_destination if changing status to emergency")
        return data

    class Meta:
        model = Route
        fields = ("id", "source", "standard_destination", "emergent_destination", "distance", 'status')


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(slug_field="name", read_only=True)
    standard_destination = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "standard_destination", 'distance')


class RouteDetailSerializer(serializers.ModelSerializer):
    source = AirportSerializer(read_only=True)
    standard_destination = AirportSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ("id", "source", "standard_destination", 'distance')


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name",)


class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
    total_rows = serializers.SerializerMethodField(help_text='A list where each element represents the number of seats in respective row of the airplane.')
    standard_number_seats_in_row = serializers.SerializerMethodField(help_text='A list where each element represents the number of seats in respective row of the airplane.')
    custom_rows_with_seat_count = serializers.SerializerMethodField(help_text='A list where each element represents the number of seats in respective row of the airplane.')



    class Meta:
        model = Airplane
        fields = (
            "id",
            "name",
            "airplane_type",
            "total_seats",
            "total_rows",
            'standard_number_seats_in_row',
            "custom_rows_with_seat_count",
            "image",
            "airline"
        )

    # @extend_schema_field(OpenApiTypes.INT, description="The date and time when the total rows were last updated")
    def get_total_rows(self, obj):
        # Return the value of the property from the model instance
        return obj.total_rows

    # @extend_schema_field(OpenApiTypes.INT, description="Average number seats in row in case when standard airplane is being created")
    def get_standard_number_seats_in_row(self, obj):
        # Return the value of the property from the model instance
          return obj.standard_number_seats_in_row()

    # @extend_schema_field(OpenApiTypes.DICT, description="Distribution of seats for each single row in case when custom airplane is being created"
    #                            "Reflected as list with integers where value means number of seats and position of integer"
    #                            "means number of row for which number of seats is distributed")
    def get_custom_rows_with_seat_count(self, obj):
        # Return the value of the property from the model instance
        if obj.standard_number_seats_in_row() is not None:
            return None
        else:
            return obj.custom_rows_with_seat_count()



class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(slug_field="name", read_only=True)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Standard Configuration",
            value={
                "total_rows": 10,
                "total_seats": 60
            }
        ),
        OpenApiExample(
            "Custom Configuration",
            value={"row_seats_distribution": [7, 7, 7, 7, 7, 7, 7, 7]}
        )
    ]
)
class AirplaneCreateSerializer(serializers.ModelSerializer):
    total_rows = serializers.IntegerField(required=False, help_text='Total number of rows in the airplane.')
    total_seats = serializers.IntegerField(required=False, help_text='Total number of seats in the airplane.')
    row_seats_distribution = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='A list where each element represents the number of seats in respective row of the airplane.'
    )

    class Meta:
        model = Airplane
        fields = ['id', 'name', 'airline', 'airplane_type', "total_rows",  "total_seats", "row_seats_distribution"]

    def validate(self, attrs):
        data = super(AirplaneCreateSerializer, self).validate(attrs=attrs)

        if "row_seats_distribution" in attrs:
            row_seats_distribution = attrs["row_seats_distribution"]
            Airplane.validate_airplane_custom(
                row_seats_distribution,
                ValidationError
            )
        else:
            total_rows = attrs["total_rows"]
            total_seats = attrs["total_seats"]
            Airplane.validate_airplane_standard(
                total_rows,
                total_seats,
                ValidationError
            )

        return data

    def create(self, validated_data):

        total_rows = validated_data.pop('total_rows', None)

        # @extend_schema_field({
        #     "name": "total_rows",
        #     "description": "Total number of rows for standard airplane (with the same number of seats in each single"
        #                    "row",
        #     "type": "integer",
        #     "format": "int32"
        # })


        total_seats = validated_data.pop('total_seats', None)


        # @extend_schema_field({
        #     "name": "total_seats",
        #     "description": "Total number of seats for standard airplane (with the same number of seats in each single"
        #                    "row",
        #     "type": "integer",
        #     "format": "int32"
        # })

        row_seats_distribution = validated_data.pop('row_seats_distribution', None)

        # @extend_schema_field({
        #     "name": "row_seats_distribution",
        #     "description": "Distribution of seats for each single row in case when custom airplane is being created"
        #                    "Reflected as list with integers where value means number of seats and position of integer"
        #                    "means number of row for which number of seats is distributed",
        #     "type": "list of dictionaries",
        #     "format": "int32"
        # })

        airplane_instance = super().create(validated_data)

        if total_rows and total_seats:
            self._create_standard_airplane(airplane_instance, total_rows, total_seats)
        elif row_seats_distribution:
            self._create_custom_airplane(airplane_instance, row_seats_distribution)
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

    def _create_custom_airplane(self, airplane, row_seats_distribution):

        for index, seats in enumerate(row_seats_distribution):
            for seat_num in range(1, seats + 1):
                seat = Seat.objects.create(
                    airplane=airplane,
                    row=index + 1,
                    seat_number=seat_num,
                )

                print(f"Создано место: {seat}")


class AirlineSerializer(serializers.ModelSerializer):
    airplanes = AirplaneSerializer(many=True, read_only=False, allow_null=True, required=False)

    overall_rating = serializers.SerializerMethodField()

    avg_boarding_deplaining = serializers.SerializerMethodField(read_only=True)
    avg_crew = serializers.SerializerMethodField(read_only=True)
    avg_services = serializers.SerializerMethodField(read_only=True)
    avg_entertainment = serializers.SerializerMethodField(read_only=True)
    avg_wi_fi = serializers.SerializerMethodField(read_only=True)

    def get_overall_rating(self, obj):
        return obj.overall_rating.get('overall_rating', 0)

    def get_avg_boarding_deplaining(self, obj):
        return obj.overall_rating.get('avg_boarding_deplaining', 0)

    def get_avg_crew(self, obj):
        return obj.overall_rating.get('avg_crew', 0)

    def get_avg_services(self, obj):
        return obj.overall_rating.get('avg_services', 0)

    def get_avg_entertainment(self, obj):
        return obj.overall_rating.get('avg_entertainment', 0)

    def get_avg_wi_fi(self, obj):
        return obj.overall_rating.get('avg_wi_fi', 0)

    def create(self, validated_data):
        if 'airplanes' in validated_data:
            airplanes_data = validated_data.pop('airplanes')
        else:
            airplanes_data = []
        if 'ratings' in validated_data:
            ratings_data = validated_data.pop('ratings')
        else:
            ratings_data = []
        airline = Airline.objects.create(**validated_data)
        for airplane_data in airplanes_data:
            Airplane.objects.create(airline=airline, **airplane_data)
        for rating_data in ratings_data:
            Airplane.objects.create(airline=airline, **rating_data)
        return airline

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
            'avg_services',
            'avg_entertainment',
            'avg_wi_fi',
            'ratings'
        )


class AirlineListSerializer(AirlineSerializer):
    class Meta:
        model = Airline
        fields = ("id", "name", "headquarter", "iata_icao")


class RatingSerializer(serializers.ModelSerializer):
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
            'wi_fi_rating',
            'created_time'
        )


class AirplaneImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ("id", "image")


class FlightSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data.get('status') in ['delayed', 'ahead'] and data.get('real_arrival_time') is None:
            raise serializers.ValidationError("Must update real_arrival_time if changing status to delayed or ahead")
        return data

    class Meta:
        model = Flight
        fields = '__all__'


class FlightListSerializer(FlightSerializer, serializers.ModelSerializer):
    route_source = serializers.CharField(
        source="route.source",
    )
    route_standard_destination = serializers.CharField(
        source="route.standard_destination", read_only=True
    )
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)
    airplane_capacity = serializers.IntegerField(
        source="airplane.capacity", read_only=True
    )
    tickets_available = serializers.SerializerMethodField(read_only=True)

    def get_tickets_available(self, obj):
        # Return the value of the property from the model instance
        return obj.tickets_available

    class Meta:
        model = Flight
        fields = (
            "id",
            "route_source",
            "route_standard_destination",
            "airplane_name",
            "airplane_capacity",
            "tickets_available",
            "departure_time",
            "estimated_arrival_time",
            "real_arrival_time"
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
            "estimated_arrival_time",
            "real_arrival_time",
            "taken_places",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_null=False)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            # Get flight instance
            flight = tickets_data[0]['flight']
            tickets_available = flight.tickets_available

            if tickets_available < len(tickets_data):
                raise serializers.ValidationError("Not enough tickets available")

            order = Order.objects.create(**validated_data)

            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)

            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
