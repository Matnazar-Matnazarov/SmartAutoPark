#!/usr/bin/env python3
"""
Simple test script to verify Smart AutoPark URLs and basic functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_urls():
    """Test all the main URLs to ensure they're accessible"""
    
    print("Testing Smart AutoPark URLs...")
    print("=" * 50)
    
    # Test URLs
    test_urls = [
        ("/", "Home page redirect"),
        ("/home/", "Home page"),
        ("/login/", "Login page"),
        ("/api/statistics/", "Statistics API"),
        ("/api/vehicle-entries/", "Vehicle entries API"),
        ("/receive-entry/", "Receive entry endpoint"),
        ("/receive-exit/", "Receive exit endpoint"),
    ]
    
    for url, description in test_urls:
        try:
            response = requests.get(f"{BASE_URL}{url}", timeout=5)
            status = response.status_code
            if status == 200:
                print(f"✅ {description}: {status}")
            elif status == 302:  # Redirect
                print(f"🔄 {description}: {status} (Redirect)")
            elif status == 405:  # Method not allowed (expected for POST-only endpoints)
                print(f"⚠️  {description}: {status} (Method not allowed - expected)")
            else:
                print(f"❌ {description}: {status}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: Connection failed (server not running?)")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")

def test_api_endpoints():
    """Test API endpoints with proper data"""
    
    print("\nTesting API endpoints...")
    print("=" * 50)
    
    # Test statistics API
    try:
        response = requests.get(f"{BASE_URL}/api/statistics/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Statistics API: {data}")
        else:
            print(f"❌ Statistics API: {response.status_code}")
    except Exception as e:
        print(f"❌ Statistics API Error: {e}")
    
    # Test vehicle entries API
    try:
        response = requests.get(f"{BASE_URL}/api/vehicle-entries/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Vehicle Entries API: {data}")
        else:
            print(f"❌ Vehicle Entries API: {response.status_code}")
    except Exception as e:
        print(f"❌ Vehicle Entries API Error: {e}")
    
    # Test add car API
    try:
        car_data = {
            "number_plate": "TEST123",
            "is_free": False,
            "is_special_taxi": False,
            "is_blocked": False
        }
        response = requests.post(
            f"{BASE_URL}/api/add-car/",
            json=car_data,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Add Car API: {data}")
        else:
            print(f"❌ Add Car API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Add Car API Error: {e}")

if __name__ == "__main__":
    print("Smart AutoPark URL and API Test")
    print("=" * 50)
    
    test_urls()
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nTo run the full test.http file:")
    print("1. Install REST Client extension in VS Code")
    print("2. Open test.http file")
    print("3. Click 'Send Request' above each test") 