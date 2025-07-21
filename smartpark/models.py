from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Role(models.TextChoices):
    OPERATOR = "operator"
    ADMIN = "admin"


class CustomUser(AbstractUser):
    image = models.ImageField(upload_to="users/", blank=True, null=True)
    role = models.CharField(max_length=50, default=Role.OPERATOR)

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
    entry_image = models.ImageField(upload_to="entries/")
    exit_image = models.ImageField(upload_to="exits/", blank=True, null=True)
    total_amount = models.IntegerField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        # Ensure timezone-aware formatting
        entry_time = self.entry_time
        return f"{self.number_plate} - {entry_time.strftime('%Y-%m-%d %H:%M')}"

    def calculate_amount(self):
        """Calculate parking fee based on time spent"""
        if not self.exit_time:
            return 0

        from config.settings import HOUR_PRICE

        # Ensure both times are timezone-aware
        entry_time = self.entry_time
        exit_time = self.exit_time

        duration = exit_time - entry_time
        hours = duration.total_seconds() / 3600

        # Round up to the nearest hour for billing
        hours = max(1, round(hours + 0.5))  # At least 1 hour, round up

        # Calculate total amount using HOUR_PRICE
        total_amount = int(hours * HOUR_PRICE)

        print(
            f"💰 Payment calculation: {hours} hours × {HOUR_PRICE} = {total_amount} so'm"
        )

        return total_amount

    def mark_as_paid(self):
        """Mark this entry as paid"""
        self.is_paid = True
        self.save()

    class Meta:
        db_table = "vehicle_entries"
        verbose_name = "Vehicle Entry"
        verbose_name_plural = "Vehicle Entries"


class Cars(models.Model):
    number_plate = models.CharField(max_length=15)
    is_free = models.BooleanField(default=False)
    is_special_taxi = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        status = []
        if self.is_free:
            status.append("Bepul")
        if self.is_special_taxi:
            status.append("Maxsus taksi")
        if self.is_blocked:
            status.append("Bloklangan")

        status_str = f" ({', '.join(status)})" if status else ""
        return f"{self.number_plate}{status_str}"

    class Meta:
        db_table = "cars"
        verbose_name = "Car"
        verbose_name_plural = "Cars"
