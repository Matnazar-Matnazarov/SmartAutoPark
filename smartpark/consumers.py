import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import datetime
from .models import VehicleEntry, Cars


class HomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the home_updates group
        await self.channel_layer.group_add("home_updates", self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to Smart AutoPark WebSocket",
                }
            )
        )

    async def disconnect(self, close_code):
        # Leave the home_updates group
        await self.channel_layer.group_discard("home_updates", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "get_statistics":
            await self.send_statistics(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_vehicle_entries":
            await self.send_vehicle_entries(
                data.get("date", timezone.now().date().isoformat()),
                data.get("number_plate", ""),
                data.get("status", "all"),
            )
        elif message_type == "mark_as_paid":
            await self.handle_mark_as_paid(data.get("entry_id"))
        elif message_type == "add_car":
            await self.handle_add_car(data)
        elif message_type == "block_car":
            await self.handle_block_car(data.get("number_plate"))
        elif message_type == "delete_entry":
            await self.handle_delete_entry(data.get("entry_id"))
        elif message_type == "get_unpaid_entries":
            await self.send_unpaid_entries(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_latest_unpaid_entry":
            await self.send_latest_unpaid_entry(
                data.get("date", timezone.now().date().isoformat())
            )
        elif message_type == "get_receipt":
            await self.handle_get_receipt(data.get("entry_id"))

    # Handle broadcast messages from signals
    async def broadcast_update(self, event):
        """Handle broadcast updates from VehicleEntry signals"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "model_update",
                    "statistics": event["statistics"],
                    "vehicle_entries": event["vehicle_entries"],
                    "action": event["action"],
                    "entry_id": event.get("entry_id"),
                    "number_plate": event.get("number_plate"),
                }
            )
        )

    async def broadcast_car_update(self, event):
        """Handle broadcast updates from Cars signals"""
        await self.send(
            text_data=json.dumps(
                {"type": "car_update", "car": event["car"], "action": event["action"]}
            )
        )

    @database_sync_to_async
    def get_statistics(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.max.time()))
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        # Get today's entries using timezone-aware datetime range
        today_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime,
            entry_time__lte=end_datetime
        )
        total_entries = today_entries.count()
        total_exits = today_entries.filter(exit_time__isnull=False).count()
        total_inside = total_entries - total_exits

        # Get unpaid entries
        unpaid_entries = today_entries.filter(
            is_paid=False, exit_time__isnull=False
        ).count()

        return {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "total_inside": total_inside,
            "unpaid_entries": unpaid_entries,
        }

    @database_sync_to_async
    def get_vehicle_entries(
        self, date_str, number_plate_filter="", status_filter="all"
    ):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.max.time()))
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        # Use timezone-aware datetime range instead of naive date
        entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime,
            entry_time__lte=end_datetime
        ).order_by("-entry_time")

        if number_plate_filter:
            entries = entries.filter(number_plate__icontains=number_plate_filter)

        # Status filter
        if status_filter == "paid":
            entries = entries.filter(is_paid=True)
        elif status_filter == "unpaid":
            entries = entries.filter(is_paid=False, exit_time__isnull=False)
        elif status_filter == "inside":
            entries = entries.filter(exit_time__isnull=True)
        elif status_filter == "exited":
            entries = entries.filter(exit_time__isnull=False)

        entries_data = []
        for entry in entries:
            # Ensure timezone-aware formatting
            entry_time = timezone.localtime(entry.entry_time) if timezone.is_naive(entry.entry_time) else entry.entry_time
            exit_time = timezone.localtime(entry.exit_time) if entry.exit_time and timezone.is_naive(entry.exit_time) else entry.exit_time
            
            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M")
                    if exit_time
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

        return entries_data

    @database_sync_to_async
    def mark_as_paid(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)
            entry.is_paid = True
            entry.save()
            return {"success": True, "entry_id": entry_id}
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    @database_sync_to_async
    def delete_entry(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)
            entry.delete()
            return {"success": True, "entry_id": entry_id}
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    @database_sync_to_async
    def get_latest_unpaid_entry(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.max.time()))
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        # Get the latest unpaid entry that has exited using timezone-aware datetime range
        latest_entry = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime,
            entry_time__lte=end_datetime,
            is_paid=False,
            exit_time__isnull=False
        ).order_by('-exit_time').first()
        
        if latest_entry:
            # Ensure timezone-aware formatting
            entry_time = timezone.localtime(latest_entry.entry_time) if timezone.is_naive(latest_entry.entry_time) else latest_entry.entry_time
            exit_time = timezone.localtime(latest_entry.exit_time) if timezone.is_naive(latest_entry.exit_time) else latest_entry.exit_time
            
            return {
                'id': latest_entry.id,
                'number_plate': latest_entry.number_plate,
                'entry_time': entry_time.strftime('%H:%M'),
                'exit_time': exit_time.strftime('%H:%M'),
                'total_amount': latest_entry.total_amount or 0,
                'duration_hours': round((exit_time - entry_time).total_seconds() / 3600, 2)
            }
        else:
            return None

    @database_sync_to_async
    def get_unpaid_entries(self, date_str):
        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(date_obj, datetime.max.time()))
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))
            end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        # Get unpaid entries that have exited using timezone-aware datetime range
        unpaid_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime,
            entry_time__lte=end_datetime,
            is_paid=False, 
            exit_time__isnull=False
        ).order_by("-exit_time")

        entries_data = []
        for entry in unpaid_entries:
            # Ensure timezone-aware formatting
            entry_time = timezone.localtime(entry.entry_time) if timezone.is_naive(entry.entry_time) else entry.entry_time
            exit_time = timezone.localtime(entry.exit_time) if timezone.is_naive(entry.exit_time) else entry.exit_time
            
            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M"),
                    "total_amount": entry.total_amount or 0,
                    "duration_hours": round(
                        (exit_time - entry_time).total_seconds() / 3600, 2
                    ),
                }
            )

        return entries_data

    @database_sync_to_async
    def get_receipt(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)

            if not entry.is_paid:
                return {"success": False, "error": "Entry is not paid"}

            # Ensure timezone-aware formatting
            entry_time = timezone.localtime(entry.entry_time) if timezone.is_naive(entry.entry_time) else entry.entry_time
            exit_time = timezone.localtime(entry.exit_time) if entry.exit_time and timezone.is_naive(entry.exit_time) else entry.exit_time

            receipt_data = {
                "id": entry.id,
                "number_plate": entry.number_plate,
                "entry_time": entry_time.strftime("%H:%M"),
                "exit_time": exit_time.strftime("%H:%M")
                if exit_time
                else None,
                "total_amount": entry.total_amount or 0,
                "is_paid": entry.is_paid,
                "duration_hours": round(
                    (exit_time - entry_time).total_seconds() / 3600, 2
                )
                if exit_time
                else 0,
            }

            return {"success": True, "receipt": receipt_data}
        except VehicleEntry.DoesNotExist:
            return {"success": False, "error": "Entry not found"}

    async def handle_get_receipt(self, entry_id):
        result = await self.get_receipt(entry_id)
        await self.send(text_data=json.dumps({"type": "receipt_data", "data": result}))

    async def handle_delete_entry(self, entry_id):
        result = await self.delete_entry(entry_id)
        await self.send(text_data=json.dumps({"type": "entry_deleted", "data": result}))

    async def send_statistics(self, date_str):
        stats = await self.get_statistics(date_str)
        await self.send(
            text_data=json.dumps({"type": "statistics_update", "data": stats})
        )

    async def send_vehicle_entries(
        self, date_str, number_plate_filter="", status_filter="all"
    ):
        entries = await self.get_vehicle_entries(
            date_str, number_plate_filter, status_filter
        )
        await self.send(
            text_data=json.dumps({"type": "vehicle_entries_update", "data": entries})
        )

    async def send_latest_unpaid_entry(self, date_str):
        entry = await self.get_latest_unpaid_entry(date_str)
        await self.send(
            text_data=json.dumps({"type": "latest_unpaid_entry_update", "data": entry})
        )

    async def send_unpaid_entries(self, date_str):
        entries = await self.get_unpaid_entries(date_str)
        await self.send(
            text_data=json.dumps({"type": "unpaid_entries_update", "data": entries})
        )

    async def handle_mark_as_paid(self, entry_id):
        result = await self.mark_as_paid(entry_id)
        await self.send(
            text_data=json.dumps({"type": "payment_update", "data": result})
        )

    async def handle_add_car(self, data):
        result = await self.add_car(data)
        await self.send(text_data=json.dumps({"type": "car_added", "data": result}))

    async def handle_block_car(self, number_plate):
        result = await self.block_car(number_plate)
        await self.send(text_data=json.dumps({"type": "car_blocked", "data": result}))
