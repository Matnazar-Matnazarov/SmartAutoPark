from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VehicleEntry, Cars
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import F
from config.settings import HOUR_PRICE
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from datetime import datetime
import xml.etree.ElementTree as ET
import re
import os
from django.utils import timezone


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'message': 'Login yoki parol xato. Iltimos tekshirib qayta urinib ko`ring!'}, status=401)
    
class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect('login')


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'home.html')


def parse_hikvision_xml(xml_content):
    """Parse Hikvision XML motion detection alert - extract ALL available data"""
    try:
        root = ET.fromstring(xml_content)
        
        # Initialize comprehensive data structure
        all_data = {
            'camera_info': {},
            'event_info': {},
            'channel_info': {},
            'motion_info': {},
            'raw_xml': xml_content,
            'parsed_at': timezone.now().isoformat()
        }
        
        # Extract all possible camera information
        camera_elements = [
            'ipAddress', 'macAddress', 'deviceID', 'deviceName', 
            'deviceDescription', 'deviceLocation', 'systemContact',
            'model', 'serialNumber', 'firmwareVersion', 'firmwareReleasedDate'
        ]
        
        for element in camera_elements:
            elem = root.find(f'.//{element}')
            if elem is not None and elem.text:
                all_data['camera_info'][element] = elem.text
        
        # Extract all possible event information
        event_elements = [
            'eventType', 'eventState', 'eventDescription', 'eventNotification',
            'dateTime', 'activePostCount', 'eventTypeString', 'eventStateString',
            'eventDescriptionString', 'eventNotificationString'
        ]
        
        for element in event_elements:
            elem = root.find(f'.//{element}')
            if elem is not None and elem.text:
                all_data['event_info'][element] = elem.text
        
        # Extract all possible channel information
        channel_elements = [
            'channelID', 'channelName', 'channelType', 'channelState',
            'channelDescription', 'channelLocation'
        ]
        
        for element in channel_elements:
            elem = root.find(f'.//{element}')
            if elem is not None and elem.text:
                all_data['channel_info'][element] = elem.text
        
        # Extract motion detection specific information
        motion_elements = [
            'motionDetection', 'motionAlarm', 'motionState', 'motionRegion',
            'motionSensitivity', 'motionThreshold', 'motionArea'
        ]
        
        for element in motion_elements:
            elem = root.find(f'.//{element}')
            if elem is not None and elem.text:
                all_data['motion_info'][element] = elem.text
        
        # Also extract any other elements that might exist
        other_elements = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                tag = elem.tag
                if (tag not in camera_elements and 
                    tag not in event_elements and 
                    tag not in channel_elements and 
                    tag not in motion_elements):
                    other_elements.append({
                        'tag': tag,
                        'value': elem.text.strip(),
                        'attributes': dict(elem.attrib) if elem.attrib else {}
                    })
        
        if other_elements:
            all_data['other_elements'] = other_elements
        
        # Create a summary for easy access
        all_data['summary'] = {
            'camera_ip': all_data['camera_info'].get('ipAddress'),
            'camera_name': all_data['camera_info'].get('deviceName'),
            'channel_id': all_data['channel_info'].get('channelID'),
            'channel_name': all_data['channel_info'].get('channelName'),
            'event_type': all_data['event_info'].get('eventType'),
            'event_state': all_data['event_info'].get('eventState'),
            'date_time': all_data['event_info'].get('dateTime'),
            'total_elements_found': len([k for k in all_data.keys() if k not in ['raw_xml', 'parsed_at', 'summary']])
        }
        
        return all_data
        
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {
            'error': str(e),
            'raw_xml': xml_content,
            'parsed_at': timezone.now().isoformat()
        }
from django.core.files.base import ContentFile
@csrf_exempt
def receive_entry(request):
    if request.method == "POST":
        content_type = request.headers.get('Content-Type', '')
        body_bytes = request.body
        body_str = body_bytes.decode('utf-8', errors='ignore')

        # 1. XML'dan davlat raqamini ajratamiz (masalan <licensePlate> tagidan)
        number_plate_match = re.search(r'<licensePlate>(.*?)</licensePlate>', body_str)
        number_plate = number_plate_match.group(1) if number_plate_match else f"TEMP{timezone.now().strftime('%H%M%S')}"

        # 2. Faylni multipart dan ajratish
        # Bu oddiy variant: multipart so‘rovdan rasmni olish
        boundary = content_type.split("boundary=")[-1] if "boundary=" in content_type else None

        if boundary:
            parts = body_bytes.split(boundary.encode())
            image_data = None
            for part in parts:
                if b'Content-Type: image/jpeg' in part:
                    image_data = part.split(b'\r\n\r\n', 1)[-1].rsplit(b'\r\n', 1)[0]
                    break
            
            if image_data:
                # 3. Fayl nomi: Raqam + sana (20250717_135501.jpg)
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{number_plate}_{timestamp}.jpg"

                # 4. Rasmdan ImageField fayl obyektini yasaymiz
                image_file = ContentFile(image_data, name=filename)

                # 5. Bazaga yozamiz
                entry = VehicleEntry.objects.create(
                    number_plate=number_plate,
                    entry_time=timezone.now(),
                    entry_image=image_file,
                    total_amount=0,
                )

                return JsonResponse({
                    "status": "ok",
                    "message": "VehicleEntry created",
                    "number_plate": number_plate,
                    "file_saved": filename,
                    "entry_id": entry.id
                })

        return JsonResponse({"error": "Image or boundary not found in request"}, status=400)

    return JsonResponse({"error": "Only POST allowed"}, status=405)




@csrf_exempt
def receive_exit(request):
    if request.method == "POST":
        from pprint import pprint
        print("\n========== HIKVISION CAMERA EXIT POST ==========")
        print("Headers:")
        pprint(dict(request.headers))
        print("\nBody (bytes, first 300):")
        print(request.body[:300])
        
        # Check if this is a Hikvision XML alert
        content_type = request.headers.get('Content-Type', '')
        body_str = request.body.decode('utf-8', errors='ignore')
        
        # Check for XML content in the request
        if '<?xml' in body_str or 'MoveDetection.xml' in body_str:
            print("📹 Hikvision exit detection alert received")
            
            # Extract XML content
            xml_content = None
            
            # Method 1: Try to get from POST data
            for key, value in request.POST.items():
                if key == 'MoveDetection.xml':
                    xml_content = value
                    break
            
            # Method 2: Extract from request body using regex
            if not xml_content:
                xml_match = re.search(r'<\?xml.*?</EventNotificationAlert>', body_str, re.DOTALL)
                if xml_match:
                    xml_content = xml_match.group(0)
            
            # Method 3: Look for XML between boundaries
            if not xml_content:
                boundary_match = re.search(r'--boundary\r\n.*?Content-Type: application/xml.*?\r\n\r\n(.*?)\r\n--boundary', body_str, re.DOTALL)
                if boundary_match:
                    xml_content = boundary_match.group(1)
            
            if xml_content:
                print(f"📄 XML Content found: {xml_content[:200]}...")
                event_data = parse_hikvision_xml(xml_content)
                
                if event_data:
                    print(f"📊 Exit Event Data: {event_data}")
                    
                    # Generate a temporary number plate based on timestamp and camera info
                    timestamp = timezone.now().strftime('%H%M%S')
                    camera_id = event_data.get('channel_id', '01')
                    number_plate = f"TEMP{camera_id}{timestamp}"
                    
                    # Find the latest entry for this car today
                    today = timezone.now().date()
                    latest_entry = VehicleEntry.objects.filter(
                        number_plate__startswith=f"TEMP{camera_id}",
                        entry_time__date=today
                    ).order_by('-entry_time').first()
                    
                    if latest_entry:
                        # Update the exit time and calculate amount
                        latest_entry.exit_time = timezone.now()
                        latest_entry.total_amount = latest_entry.calculate_amount()
                        latest_entry.save()
                        
                        print(f"✅ Vehicle exit updated: {latest_entry.number_plate}")
                        print(f"📹 Exit detected at: {event_data.get('date_time')}")
                        print(f"📷 Camera: {event_data.get('channel_name')} (IP: {event_data.get('ip_address')})")
                        print(f"💰 Amount: {latest_entry.total_amount} so'm")
                        
                        return JsonResponse({
                            "status": "ok",
                            "message": "Exit detection processed",
                            "number_plate": latest_entry.number_plate,
                            "event_data": event_data,
                            "camera_ip": event_data.get('ip_address'),
                            "camera_channel": event_data.get('channel_id'),
                            "event_time": event_data.get('date_time'),
                            "amount": latest_entry.total_amount
                        })
                    else:
                        print("❌ No entry found for exit")
                        return JsonResponse({"error": "No entry found for exit"}, status=404)
                        
                else:
                    print("❌ Failed to parse XML data")
                    return JsonResponse({"error": "Invalid XML format"}, status=400)
            else:
                print("❌ No XML content found in request")
                return JsonResponse({"error": "No XML content"}, status=400)
        
        else:
            # Handle regular form data (manual exit)
            number_plate = request.POST.get('number_plate')
            print(f"🚗 Manual exit - Number Plate: {number_plate}")
            
            if number_plate:
                try:
                    car, created = Cars.objects.get_or_create(number_plate=number_plate)
                    today = timezone.now().date()
                    
                    # Get the latest entry for this car today
                    latest_entry = VehicleEntry.objects.filter(
                        number_plate=number_plate, 
                        entry_time__date=today
                    ).order_by('-entry_time').first()
                    
                    if latest_entry:
                        if car.is_free:
                            latest_entry.exit_image = request.FILES.get('exit_image')
                            latest_entry.total_amount = 0
                            latest_entry.exit_time = timezone.now()
                            latest_entry.save()
                        elif car.is_special_taxi and not car.is_blocked:
                            latest_entry.exit_image = request.FILES.get('exit_image')
                            latest_entry.total_amount = 0
                            latest_entry.exit_time = timezone.now()
                            latest_entry.save()
                        else:
                            if not car.is_blocked:
                                latest_entry.exit_image = request.FILES.get('exit_image')
                                latest_entry.exit_time = timezone.now()
                                latest_entry.total_amount = latest_entry.calculate_amount()
                                latest_entry.save()
                        
                        print("✅ Vehicle exit updated successfully")
                        return JsonResponse({
                            "status": "ok", 
                            "number_plate": number_plate,
                            "amount": latest_entry.total_amount
                        })
                    else:
                        print("❌ No entry found for this car today")
                        return JsonResponse({"error": "No entry found for this car today"}, status=404)
                        
                except Exception as e:
                    print(f"❌ Error updating vehicle exit: {e}")
                    return JsonResponse({"error": str(e)}, status=500)
            else:
                print("❌ No number plate provided")
                return JsonResponse({"error": "Number plate is required"}, status=400)

        print("================================\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Only POST allowed"}, status=405)


# New API endpoints for WebSocket functionality

@csrf_exempt
@require_http_methods(["GET"])
def get_statistics(request):
    """Get statistics for a specific date"""
    date_str = request.GET.get('date', timezone.now().date().isoformat())
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        date = timezone.now().date()
    
    today_entries = VehicleEntry.objects.filter(entry_time__date=date)
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(is_paid=False, exit_time__isnull=False).count()
    
    return JsonResponse({
        'total_entries': total_entries,
        'total_exits': total_exits,
        'total_inside': total_inside,
        'unpaid_entries': unpaid_entries
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_vehicle_entries(request):
    """Get vehicle entries for a specific date"""
    date_str = request.GET.get('date', timezone.now().date().isoformat())
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
    
    return JsonResponse({'entries': entries_data})


@csrf_exempt
@require_http_methods(["POST"])
def mark_as_paid(request):
    """Mark a vehicle entry as paid"""
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        
        entry = VehicleEntry.objects.get(id=entry_id)
        entry.is_paid = True
        entry.save()
        
        return JsonResponse({'success': True, 'entry_id': entry_id})
    except VehicleEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Entry not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def add_car(request):
    """Add or update a car with boolean flags"""
    try:
        data = json.loads(request.body)
        number_plate = data.get('number_plate')
        is_free = data.get('is_free', False)
        is_special_taxi = data.get('is_special_taxi', False)
        is_blocked = data.get('is_blocked', False)
        
        if not number_plate:
            return JsonResponse({'success': False, 'error': 'Number plate is required'}, status=400)
        
        car, created = Cars.objects.get_or_create(
            number_plate=number_plate,
            defaults={
                'is_free': is_free,
                'is_special_taxi': is_special_taxi,
                'is_blocked': is_blocked
            }
        )
        
        if not created:
            car.is_free = is_free
            car.is_special_taxi = is_special_taxi
            car.is_blocked = is_blocked
            car.save()
        
        return JsonResponse({
            'success': True,
            'car': {
                'number_plate': car.number_plate,
                'is_free': car.is_free,
                'is_special_taxi': car.is_special_taxi,
                'is_blocked': car.is_blocked
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def block_car(request):
    """Block a car by number plate"""
    try:
        data = json.loads(request.body)
        number_plate = data.get('number_plate')
        
        if not number_plate:
            return JsonResponse({'success': False, 'error': 'Number plate is required'}, status=400)
        
        car = Cars.objects.get(number_plate=number_plate)
        car.is_blocked = True
        car.save()
        
        return JsonResponse({'success': True, 'number_plate': number_plate})
    except Cars.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Car not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


