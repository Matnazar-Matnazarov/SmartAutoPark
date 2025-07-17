#!/usr/bin/env python3
"""
Test script to verify Django signals and WebSocket updates
"""
import os
import sys
import django
import asyncio
import websockets
import json
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from smartpark.models import VehicleEntry, Cars
from django.utils import timezone

async def test_websocket_signals():
    """Test WebSocket connection and listen for signal updates"""
    uri = "ws://localhost:8000/ws/home/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Listen for messages
            print("🔍 Listening for signal updates...")
            print("📝 Create/update models in Django admin or via API to see updates")
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(message)
                    print(f"\n📨 Received message: {data['type']}")
                    
                    if data['type'] == 'model_update':
                        print(f"🚗 Vehicle Entry {data['action']}: {data['number_plate']}")
                        print(f"📊 Statistics: {data['statistics']}")
                        print(f"📋 Entries count: {len(data['vehicle_entries'])}")
                    elif data['type'] == 'car_update':
                        print(f"🚙 Car {data['action']}: {data['car']['number_plate']}")
                        print(f"🔧 Car data: {data['car']}")
                    else:
                        print(f"📄 Other message: {data}")
                        
                except asyncio.TimeoutError:
                    print("⏰ No messages received in 30 seconds...")
                    break
                    
    except websockets.exceptions.ConnectionRefused:
        print("❌ Could not connect to WebSocket server. Make sure the server is running.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def test_model_creation():
    """Test creating models to trigger signals"""
    print("\n🧪 Testing model creation to trigger signals...")
    
    try:
        # Test creating a car
        car, created = Cars.objects.get_or_create(
            number_plate="SIGNAL_TEST",
            defaults={
                'is_free': True,
                'is_special_taxi': False,
                'is_blocked': False
            }
        )
        
        if created:
            print(f"✅ Created car: {car.number_plate}")
        else:
            print(f"ℹ️  Car already exists: {car.number_plate}")
        
        # Test creating a vehicle entry
        entry = VehicleEntry.objects.create(
            number_plate="SIGNAL_TEST",
            total_amount=0,
            is_paid=False
        )
        print(f"✅ Created vehicle entry: {entry.number_plate}")
        
        # Test updating the entry
        entry.total_amount = 5000
        entry.save()
        print(f"✅ Updated vehicle entry: {entry.number_plate}")
        
        # Test marking as paid
        entry.is_paid = True
        entry.save()
        print(f"✅ Marked entry as paid: {entry.number_plate}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test models: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Smart AutoPark Signals Test")
    print("=" * 50)
    
    # Test model creation
    if test_model_creation():
        print("\n✅ Model creation tests passed")
    else:
        print("\n❌ Model creation tests failed")
        return
    
    # Test WebSocket signals
    print("\n🔌 Testing WebSocket signal updates...")
    print("💡 This will listen for 30 seconds for any signal updates")
    
    if await test_websocket_signals():
        print("\n✅ WebSocket signal tests completed")
    else:
        print("\n❌ WebSocket signal tests failed")
    
    print("\n" + "=" * 50)
    print("🎯 Test completed!")
    print("\n💡 To see real-time updates:")
    print("1. Keep this script running")
    print("2. Open another terminal and create/update models")
    print("3. Watch for WebSocket messages here")

if __name__ == "__main__":
    asyncio.run(main()) 