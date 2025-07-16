from django.db import models
from django.utils import timezone


class CustomUser(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=150)
    image = models.ImageField(upload_to='users/', blank=True, null=True)
    role = models.CharField(max_length=50,default="operator")
    
    def __str__(self):
        return self.username
    
    class Meta:
        db_table = "custom_users"
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"

class VehicleEntry(models.Model):
    number_plate = models.CharField(max_length=15)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(blank=True, null=True)
    entry_image = models.ImageField(upload_to='entries/')
    exit_image = models.ImageField(upload_to='exits/', blank=True, null=True)
    total_amount = models.IntegerField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.number_plate} - {self.entry_time.strftime('%Y-%m-%d %H:%M')}"
    

    class Meta:
        db_table = "vehicle_entries"
        verbose_name = "Vehicle Entry"
        verbose_name_plural = "Vehicle Entries"

class Cars(models.Model):
    number_plate = models.CharField(max_length=15)
    is_free = models.BooleanField(default=False)
    is_special_taxi = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    class Meta:
        db_table = "cars"
        verbose_name = "Car"
        verbose_name_plural = "Cars"
    
    