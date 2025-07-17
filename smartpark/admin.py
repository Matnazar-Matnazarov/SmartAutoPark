from django.contrib import admin
from .models import CustomUser, VehicleEntry, Cars

admin.site.register(CustomUser)
admin.site.register(VehicleEntry)
admin.site.register(Cars)
