from django.contrib import admin

from .models import (
    Country,
    City,
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Airlines,
    Flight,
    Order,
    Ticket, Seat,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country")


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("name", "closest_big_city")
    list_filter = ("closest_big_city",)
    search_fields = ("name",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("source", "destination", "distance")
    list_filter = ("source",)


@admin.register(Airlines)
class AirlinesAdmin(admin.ModelAdmin):
    list_display = ("name", "headquarter", "web_site_address")
    list_filter = ("name",)
    search_fields = ("name",)


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = ("name", "get_total_rows", "get_rows_with_seats_count")

    def get_total_rows(self, obj):
        return obj.total_rows

    get_total_rows.short_description = "Total Rows"

    def get_rows_with_seats_count(self, obj):
        return obj.rows_with_seat_count()

    get_rows_with_seats_count.short_description = "Rows with seats"

    # class MyModelAdmin(admin.ModelAdmin):
    #     list_display = ('my_property_display', 'other_field', 'another_field')
    #
    #     def my_property_display(self, obj):
    #         return obj.my_property
    #
    #     my_property_display.short_description = "My Property"


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("row", "seat_number", "airplane")
    # list_filter = ("route",)


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ("route", "airplane", "departure_time", "arrival_time")
    list_filter = ("route",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("order", "flight", "row", "seat")
    list_filter = ("flight",)


admin.site.register(Country)
admin.site.register(AirplaneType)
# admin.site.unregister(Airlines)
admin.site.register(Order)
