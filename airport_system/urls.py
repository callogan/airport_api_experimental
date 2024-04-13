from django.urls import path

from rest_framework import routers
from .views import (
    CountryViewSet,
    CityViewSet,
    AirportViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    RouteViewSet,
    FlightViewSet,
    OrderViewSet, AirlineViewSet, AllocateTicketAPIView, AirlineRatingViewSet,
    # AllocateTicketViewSet
)

router = routers.DefaultRouter()
router.register("countries", CountryViewSet)
router.register("cities", CityViewSet)
router.register("airports", AirportViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("airlines", AirlineViewSet)
router.register("routes", RouteViewSet)
router.register("flights", FlightViewSet)
router.register("orders", OrderViewSet)
router.register("ratings", AirlineRatingViewSet)
# router.register('tickets/<int:ticket_id>/allocate/', AllocateTicketAPIView.as_view(), basename="ticket_allocate")

urlpatterns = router.urls + [
    # path('ratings/', AirlineRatingViewSet.as_view({'get': 'list', 'post': 'create'}), name='rating-list'),
    path('tickets/<int:ticket_id>/allocate/', AllocateTicketAPIView.as_view(), name='ticket_allocate'), #redundant
]

app_name = "airport_system"
