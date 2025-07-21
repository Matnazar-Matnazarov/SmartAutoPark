from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VehicleEntry, Cars
from django.utils import timezone
from datetime import datetime


@receiver(post_save, sender=VehicleEntry)
def vehicle_entry_updated(sender, instance, created, **kwargs):
    """Send WebSocket update when VehicleEntry is created or updated"""
    channel_layer = get_channel_layer()

    # Get statistics for today using timezone-aware datetime range
    today = timezone.now().date()
    start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(
        is_paid=False, exit_time__isnull=False
    ).count()

    # Prepare statistics data
    stats_data = {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "total_inside": total_inside,
        "unpaid_entries": unpaid_entries,
    }

    # Get all vehicle entries using timezone-aware datetime range (not just 10)
    entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    ).order_by("-entry_time")
    entries_data = []

    for entry in entries:
        entries_data.append(
            {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry.entry_time.strftime("%H:%M"),
                "exit_time": entry.exit_time.strftime("%H:%M")
                if entry.exit_time
                else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "entry_image": entry.entry_image.url if entry.entry_image else None,
                "exit_image": entry.exit_image.url if entry.exit_image else None,
                "status": "inside"
                if not entry.exit_time
                else ("paid" if entry.is_paid else "unpaid"),
            }
        )

    # Determine action type
    action = "created" if created else "updated"
    if not created and instance.is_paid:
        action = "payment_completed"

    # Broadcast update to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_update",
            "statistics": stats_data,
            "vehicle_entries": entries_data,
            "action": action,
            "entry_id": instance.id,
            "number_plate": instance.number_plate,
        },
    )


@receiver(post_delete, sender=VehicleEntry)
def vehicle_entry_deleted(sender, instance, **kwargs):
    """Send WebSocket update when VehicleEntry is deleted"""
    channel_layer = get_channel_layer()

    # Get updated statistics for today using timezone-aware datetime range
    today = timezone.now().date()
    start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(
        is_paid=False, exit_time__isnull=False
    ).count()

    # Prepare statistics data
    stats_data = {
        "total_entries": total_entries,
        "total_exits": total_exits,
        "total_inside": total_inside,
        "unpaid_entries": unpaid_entries,
    }

    # Get latest vehicle entries using timezone-aware datetime range
    entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    ).order_by("-entry_time")[:10]
    entries_data = []

    for entry in entries:
        entries_data.append(
            {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry.entry_time.strftime("%H:%M"),
                "exit_time": entry.exit_time.strftime("%H:%M")
                if entry.exit_time
                else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "entry_image": entry.entry_image.url if entry.entry_image else None,
                "exit_image": entry.exit_image.url if entry.exit_image else None,
                "status": "inside"
                if not entry.exit_time
                else ("paid" if entry.is_paid else "unpaid"),
            }
        )

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_update",
            "statistics": stats_data,
            "vehicle_entries": entries_data,
            "action": "deleted",
            "entry_id": instance.id,
            "number_plate": instance.number_plate,
        },
    )


@receiver(post_save, sender=Cars)
def car_updated(sender, instance, created, **kwargs):
    """Send WebSocket update when Cars is created or updated"""
    channel_layer = get_channel_layer()

    # Prepare car data
    car_data = {
        "id": instance.id,
        "number_plate": instance.number_plate,
        "is_free": instance.is_free,
        "is_special_taxi": instance.is_special_taxi,
        "is_blocked": instance.is_blocked,
    }

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_car_update",
            "car": car_data,
            "action": "created" if created else "updated",
        },
    )


@receiver(post_delete, sender=Cars)
def car_deleted(sender, instance, **kwargs):
    """Send WebSocket update when Cars is deleted"""
    channel_layer = get_channel_layer()

    # Send updates to all connected clients
    async_to_sync(channel_layer.group_send)(
        "home_updates",
        {
            "type": "broadcast_car_update",
            "car": {
                "number_plate": instance.number_plate,
                "is_free": instance.is_free,
                "is_special_taxi": instance.is_special_taxi,
                "is_blocked": instance.is_blocked,
            },
            "action": "deleted",
        },
    )
