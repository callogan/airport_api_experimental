from rest_framework import routers
from .views import (
    CountryViewSet,
    CityViewSet,
    AirportViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    RouteViewSet,
    FlightViewSet,
    OrderViewSet, AirlinesViewSet,
)

router = routers.DefaultRouter()
router.register("countries", CountryViewSet)
router.register("cities", CityViewSet)
router.register("airports", AirportViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("airlines", AirlinesViewSet)
router.register("routes", RouteViewSet)
router.register("flights", FlightViewSet)
router.register("orders", OrderViewSet)

urlpatterns = router.urls

app_name = "airport_system"
