from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, VehicleEntry, Cars

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'role')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('image', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('image', 'role')}),
    )

@admin.register(VehicleEntry)
class VehicleEntryAdmin(admin.ModelAdmin):
    list_display = ('number_plate', 'entry_time', 'exit_time', 'is_paid', 'total_amount')
    list_filter = ('is_paid', 'entry_time', 'exit_time')
    search_fields = ('number_plate',)
    readonly_fields = ('entry_image', 'exit_image', 'total_amount')
    date_hierarchy = 'entry_time'

@admin.register(Cars)
class CarsAdmin(admin.ModelAdmin):
    list_display = ('number_plate', 'is_free', 'is_special_taxi', 'is_blocked', 'position')
    list_filter = ('is_free', 'is_special_taxi', 'is_blocked')
    search_fields = ('number_plate', 'position')
    readonly_fields = ('license_file',)
