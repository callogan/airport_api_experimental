from datetime import datetime

import pytz
from django.db.models import F, Count, Q, Avg
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.mixins import UpdateModelMixin, CreateModelMixin, ListModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import (
    Country,
    City,
    Airport,
    Airplane,
    AirplaneType,
    Route,
    Flight,
    Order, Airline, AirlineRating, Airline, Ticket,
)

from .serializers import (
    CountrySerializer,
    CitySerializer,
    CityListSerializer,
    AirportSerializer,
    AirportListSerializer,
    AirplaneTypeSerializer,
    AirplaneSerializer,
    AirplaneListSerializer,
    # CrewSerializer,
    # CrewListSerializer,
    # CrewImageSerializer,
    RouteSerializer,
    RouteListSerializer,
    RouteDetailSerializer,
    FlightSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderSerializer,
    OrderListSerializer, AirplaneImageSerializer, AirlineSerializer, AirlineListSerializer, AirplaneCreateSerializer,
    RatingSerializer, TicketSerializer,
)


class CountryViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class CityViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = City.objects.select_related("country")
    serializer_class = CitySerializer

    def get_serializer_class(self):
        if self.action == "list":
            return CityListSerializer

        return self.serializer_class


class AirportViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Airport.objects.select_related("closest_big_city")
    serializer_class = AirportSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return AirportListSerializer

        return self.serializer_class


class AirplaneTypeViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer


class AirplaneViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Airplane.objects.select_related("airplane_type")
    serializer_class = AirplaneSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return AirplaneListSerializer
        if self.action == "create":
            return AirplaneCreateSerializer
        if self.action == "upload_image":
            return AirplaneImageSerializer

        return self.serializer_class

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        # permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        airplane = self.get_object()
        serializer = self.get_serializer(airplane, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class AirlineViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer

    def retrieve(self, request, *args, **kwargs):
        airline = self.get_object()
        # airline = get_object_or_404(Airline, pk=pk)
        # ratings = airline.rating_set.all()
        ratings = airline.ratings.all()

        # рассчитываем рейтинги
        boarding_deplaining_rating = ratings.aggregate(avg=Avg('boarding_deplaining_rating'))['avg']
        crew_rating = ratings.aggregate(avg=Avg('crew_rating'))['avg']
        entertainment_rating = ratings.aggregate(avg=Avg('entertainment_rating'))['avg']
        services_rating = ratings.aggregate(avg=Avg('services_rating'))['avg']
        wi_fi_rating = ratings.aggregate(avg=Avg('wi_fi_rating'))['avg']

        boarding_deplaining_rating = boarding_deplaining_rating if boarding_deplaining_rating is not None else 0
        crew_rating = crew_rating if crew_rating is not None else 0
        entertainment_rating = entertainment_rating if entertainment_rating is not None else 0
        services_rating = services_rating if services_rating is not None else 0
        wi_fi_rating = wi_fi_rating if wi_fi_rating is not None else 0

        # считаем средневзвешенный рейтинг
        total_score = boarding_deplaining_rating * 0.05 + crew_rating * 0.2 + services_rating * 0.15 + entertainment_rating * 0.1 + wi_fi_rating * 0.05
        total_weight = 0.05 + 0.2 + 0.15 + 0.1 + 0.05
        overall_rating = total_score / total_weight

        # # записываем рейтинги
        # airline.boarding_deplaining_rating = boarding_deplaining_rating
        # airline.crew_rating = crew_rating
        # airline.entertainment_rating = entertainment_rating
        # airline.services_rating = services_rating
        # airline.wi_fi_rating = wi_fi_rating
        # airline.save()

        data = AirlineSerializer(airline).data
        return Response(data)

    def update(self, request, pk):
        airline = self.get_object()
        print(f"Содержимое request.data: {request.data}")
        serializer = AirlineSerializer(airline, data=request.data)
        serializer.is_valid(raise_exception=True)
        # serializer.update_rating(airline, request.data)
        serializer.save()

        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == "list":
            return AirlineListSerializer

        if self.action == "retrieve":
            return AirlineSerializer

        return self.serializer_class


class AirlineRatingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = AirlineRating.objects.all()
    serializer_class = RatingSerializer


class RouteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.select_related(
        "source",
        "destination",
    )
    serializer_class = RouteSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer

        if self.action == "retrieve":
            return RouteDetailSerializer

        return RouteSerializer

    def get_queryset(self):
        country_from = self.request.query_params.get("country_from")
        country_to = self.request.query_params.get("country_to")
        city_from = self.request.query_params.get("city_from")
        city_to = self.request.query_params.get("city_to")
        route = self.request.query_params.get("route")

        if country_from:
            self.queryset = self.queryset.filter(
                source__closest_big_city__country__name__icontains=country_from
            )

        if country_to:
            self.queryset = self.queryset.filter(
                destination__closest_big_city__country__name__icontains=country_to
            )

        if city_from:
            self.queryset = self.queryset.filter(
                source__closest_big_city__name__icontains=city_from
            )

        if city_to:
            self.queryset = self.queryset.filter(
                source__closest_big_city__name__icontains=city_to
            )

        if route:
            route = route.split("-")
            self.queryset = self.queryset.filter(
                Q(source__closest_big_city__name__icontains=route[0]),
                Q(destination__closest_big_city__name__icontains=route[-1]),
            )
        return self.queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="country_from",
                description="Filter by country of departure (ex. ?country_from=the United States)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="country_to",
                description="Filter by country of destination (ex. ?country_to=Germany)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="city_from",
                description="Filter by city of departure (ex. ?city_from=New York)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="city_to",
                description="Filter by city of destination (ex. ?city_to=Berlin)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="route",
                description="Filter by city of departure & city of destination (ex. ?route=New York-Berlin)",
                type=OpenApiTypes.STR
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FlightViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Flight.objects.select_related(
            "route",
            "airplane",
            "route__destination__closest_big_city",
            "route__source__closest_big_city",
        )
        .select_related("route__airline")
    )
    serializer_class = FlightSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer

        if self.action == "retrieve":
            return FlightDetailSerializer

        return FlightSerializer

    def get_queryset(self):
        airport_from = self.request.query_params.get("airport_from")
        airport_to = self.request.query_params.get("airport_to")
        date = self.request.query_params.get("date")

        if airport_from:
            self.queryset = self.queryset.filter(route__source__name__icontains=airport_from)

        if airport_to:
            self.queryset = self.queryset.filter(route__destination__name__icontains=airport_to)

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            self.queryset = self.queryset.filter(departure_time__date=date)

        return self.queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="airport_from",
                description="Filter by airport of departure (ex. ?airport_from=JFK)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="airport_to",
                description="Filter by airport of destination (ex. ?airport_to=Berlin Central)",
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name="date",
                description="Filter by date of departure (ex. ?date=2024-01-18)",
                type=OpenApiTypes.DATE
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        fields_to_update = ["arrival_time"]
        return self.partial_update(request, *args, fields=fields_to_update, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.prefetch_related("tickets__flight__route")
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AllocateTicketAPIView(GenericAPIView):

    serializer_class = TicketSerializer

    def patch(self, request, ticket_id):
        try:
            ticket = Ticket.objects.get(pk=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        if ticket.type == "completed":
            return Response({"error": "Ticket is already allocated"}, status=status.HTTP_400_BAD_REQUEST)
        #
        # try:
        #     row = int(request.data.get('row'))
        #     seat = int(request.data.get('seat'))
        # except (ValueError, TypeError):
        #     return Response({"error": "Invalid row or seat value"}, status=status.HTTP_400_BAD_REQUEST)

        ticket.allocate_seat()
        ticket.save()

        serializer = TicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_200_OK)
