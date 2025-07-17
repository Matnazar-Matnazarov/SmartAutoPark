import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import datetime, timedelta
from .models import VehicleEntry, Cars
from django.db.models import Count, Q


class HomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the home_updates group
        await self.channel_layer.group_add("home_updates", self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to Smart AutoPark WebSocket'
        }))

    async def disconnect(self, close_code):
        # Leave the home_updates group
        await self.channel_layer.group_discard("home_updates", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'get_statistics':
            await self.send_statistics(data.get('date', timezone.now().date().isoformat()))
        elif message_type == 'get_vehicle_entries':
            await self.send_vehicle_entries(data.get('date', timezone.now().date().isoformat()))
        elif message_type == 'mark_as_paid':
            await self.handle_mark_as_paid(data.get('entry_id'))
        elif message_type == 'add_car':
            await self.handle_add_car(data)
        elif message_type == 'block_car':
            await self.handle_block_car(data.get('number_plate'))

    # Handle broadcast messages from signals
    async def broadcast_update(self, event):
        """Handle broadcast updates from VehicleEntry signals"""
        await self.send(text_data=json.dumps({
            'type': 'model_update',
            'statistics': event['statistics'],
            'vehicle_entries': event['vehicle_entries'],
            'action': event['action'],
            'entry_id': event.get('entry_id'),
            'number_plate': event.get('number_plate')
        }))

    async def broadcast_car_update(self, event):
        """Handle broadcast updates from Cars signals"""
        await self.send(text_data=json.dumps({
            'type': 'car_update',
            'car': event['car'],
            'action': event['action']
        }))

    @database_sync_to_async
    def get_statistics(self, date_str):
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date = timezone.now().date()
        
        # Get today's entries
        today_entries = VehicleEntry.objects.filter(entry_time__date=date)
        total_entries = today_entries.count()
        total_exits = today_entries.filter(exit_time__isnull=False).count()
        total_inside = total_entries - total_exits
        
        # Get unpaid entries
        unpaid_entries = today_entries.filter(is_paid=False, exit_time__isnull=False).count()
        
        return {
            'total_entries': total_entries,
            'total_exits': total_exits,
            'total_inside': total_inside,
            'unpaid_entries': unpaid_entries
        }

    @database_sync_to_async
    def get_vehicle_entries(self, date_str):
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date = timezone.now().date()
        
        entries = VehicleEntry.objects.filter(entry_time__date=date).order_by('-entry_time')[:10]
        
        entries_data = []
        for entry in entries:
            entries_data.append({
                'id': entry.id,
                'number_plate': entry.number_plate,
                'entry_time': entry.entry_time.strftime('%H:%M'),
                'exit_time': entry.exit_time.strftime('%H:%M') if entry.exit_time else None,
                'total_amount': entry.total_amount or 0,
                'is_paid': entry.is_paid,
                'entry_image': entry.entry_image.url if entry.entry_image else None,
                'exit_image': entry.exit_image.url if entry.exit_image else None,
            })
        
        return entries_data

    @database_sync_to_async
    def mark_as_paid(self, entry_id):
        try:
            entry = VehicleEntry.objects.get(id=entry_id)
            entry.is_paid = True
            entry.save()
            return {'success': True, 'entry_id': entry_id}
        except VehicleEntry.DoesNotExist:
            return {'success': False, 'error': 'Entry not found'}

    @database_sync_to_async
    def add_car(self, data):
        try:
            car, created = Cars.objects.get_or_create(
                number_plate=data.get('number_plate'),
                defaults={
                    'is_free': data.get('is_free', False),
                    'is_special_taxi': data.get('is_special_taxi', False),
                    'is_blocked': data.get('is_blocked', False)
                }
            )
            
            if not created:
                car.is_free = data.get('is_free', False)
                car.is_special_taxi = data.get('is_special_taxi', False)
                car.is_blocked = data.get('is_blocked', False)
                car.save()
            
            return {'success': True, 'car': {
                'number_plate': car.number_plate,
                'is_free': car.is_free,
                'is_special_taxi': car.is_special_taxi,
                'is_blocked': car.is_blocked
            }}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @database_sync_to_async
    def block_car(self, number_plate):
        try:
            car = Cars.objects.get(number_plate=number_plate)
            car.is_blocked = True
            car.save()
            return {'success': True, 'number_plate': number_plate}
        except Cars.DoesNotExist:
            return {'success': False, 'error': 'Car not found'}

    async def send_statistics(self, date_str):
        stats = await self.get_statistics(date_str)
        await self.send(text_data=json.dumps({
            'type': 'statistics_update',
            'data': stats
        }))

    async def send_vehicle_entries(self, date_str):
        entries = await self.get_vehicle_entries(date_str)
        await self.send(text_data=json.dumps({
            'type': 'vehicle_entries_update',
            'data': entries
        }))

    async def handle_mark_as_paid(self, entry_id):
        result = await self.mark_as_paid(entry_id)
        await self.send(text_data=json.dumps({
            'type': 'payment_update',
            'data': result
        }))

    async def handle_add_car(self, data):
        result = await self.add_car(data)
        await self.send(text_data=json.dumps({
            'type': 'car_added',
            'data': result
        }))

    async def handle_block_car(self, number_plate):
        result = await self.block_car(number_plate)
        await self.send(text_data=json.dumps({
            'type': 'car_blocked',
            'data': result
        }))
