from django.contrib import admin
from .models import Country, Business, Service, Product, Order, OpeningHour, Cart, Message, State, Event

admin.site.register(Country)
admin.site.register(Business)
admin.site.register(Service)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OpeningHour)
admin.site.register(Cart)
admin.site.register(Message)
admin.site.register(State)
admin.site.register(Event)
