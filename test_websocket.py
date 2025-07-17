#!/usr/bin/env python3
"""
Simple WebSocket test script for Smart AutoPark
"""
import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/ws/home/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")
            
            # Test getting statistics
            print("\n1. Testing statistics...")
            await websocket.send(json.dumps({
                "type": "get_statistics",
                "date": "2024-01-01"
            }))
            
            response = await websocket.recv()
            print(f"Statistics response: {response}")
            
            # Test getting vehicle entries
            print("\n2. Testing vehicle entries...")
            await websocket.send(json.dumps({
                "type": "get_vehicle_entries",
                "date": "2024-01-01"
            }))
            
            response = await websocket.recv()
            print(f"Vehicle entries response: {response}")
            
            # Test adding a car
            print("\n3. Testing add car...")
            await websocket.send(json.dumps({
                "type": "add_car",
                "number_plate": "TEST123",
                "is_free": True,
                "is_special_taxi": False,
                "is_blocked": False
            }))
            
            response = await websocket.recv()
            print(f"Add car response: {response}")
            
            # Test blocking a car
            print("\n4. Testing block car...")
            await websocket.send(json.dumps({
                "type": "block_car",
                "number_plate": "TEST123"
            }))
            
            response = await websocket.recv()
            print(f"Block car response: {response}")
            
    except websockets.exceptions.ConnectionRefused:
        print("Error: Could not connect to WebSocket server. Make sure the server is running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Testing Smart AutoPark WebSocket functionality...")
    asyncio.run(test_websocket())
    print("\nTest completed successfully!") 