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
from django.core.files.base import ContentFile

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
        content_type = request.headers.get('Content-Type', '')
        body_bytes = request.body
        body_str = body_bytes.decode('utf-8', errors='ignore')
        car, created = Cars.objects.get_or_create(number_plate=number_plate)
        today = timezone.now()
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

           
            try:
      
                
                # Get the latest entry for this car today
                latest_entry = VehicleEntry.objects.filter(
                    number_plate=number_plate, 
                    entry_time__date=today
                ).order_by('-entry_time').first()
                
                if latest_entry:
                    if car.is_free and not car.is_blocked:
                        latest_entry.exit_image = image_file
                        latest_entry.total_amount = 0
                        latest_entry.exit_time = timezone.now()
                        latest_entry.save()
                    elif car.is_special_taxi and not car.is_blocked:
                        latest_entry.exit_image = image_file
                        latest_entry.total_amount = latest_entry.calculate_amount() if VehicleEntry.objects.filter(entry_time=today, number_plate=number_plate).count()<2 else 0
                        latest_entry.exit_time = timezone.now()
                        latest_entry.save()
                    else:
                        if not car.is_blocked:
                            latest_entry.exit_image = image_file
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

        return JsonResponse({"error": "Image or boundary not found in request"}, status=400)




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
    """Get vehicle entries for a specific date with filters"""
    try:
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        number_plate_filter = request.GET.get('number_plate', '')
        status_filter = request.GET.get('status', 'all')  # all, paid, unpaid, inside, exited
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date = timezone.now().date()
        
        entries = VehicleEntry.objects.filter(entry_time__date=date).order_by('-entry_time')
        
        if number_plate_filter:
            entries = entries.filter(number_plate__icontains=number_plate_filter)
        
        # Status filter
        if status_filter == 'paid':
            entries = entries.filter(is_paid=True)
        elif status_filter == 'unpaid':
            entries = entries.filter(is_paid=False, exit_time__isnull=False)
        elif status_filter == 'inside':
            entries = entries.filter(exit_time__isnull=True)
        elif status_filter == 'exited':
            entries = entries.filter(exit_time__isnull=False)
        
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
                'status': 'inside' if not entry.exit_time else ('paid' if entry.is_paid else 'unpaid')
            })
        
        return JsonResponse({"status": "ok", "entries": entries_data})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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


@csrf_exempt
@require_http_methods(["POST"])
def delete_entry(request):
    """Soft delete a vehicle entry"""
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        
        if not entry_id:
            return JsonResponse({'success': False, 'error': 'Entry ID is required'}, status=400)
        
        entry = VehicleEntry.objects.get(id=entry_id)
        entry.soft_delete()
        
        return JsonResponse({'success': True, 'entry_id': entry_id})
    except VehicleEntry.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Entry not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def get_unpaid_entries(request):
    """Get unpaid entries for receipt printing"""
    try:
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            date = timezone.now().date()
        
        # Get unpaid entries that have exited
        unpaid_entries = VehicleEntry.objects.filter(
            entry_time__date=date,
            is_paid=False,
            exit_time__isnull=False
        ).order_by('-exit_time')
        
        entries_data = []
        for entry in unpaid_entries:
            entries_data.append({
                'id': entry.id,
                'number_plate': entry.number_plate,
                'entry_time': entry.entry_time.strftime('%H:%M'),
                'exit_time': entry.exit_time.strftime('%H:%M'),
                'total_amount': entry.total_amount or 0,
                'duration_hours': round((entry.exit_time - entry.entry_time).total_seconds() / 3600, 2)
            })
        
        return JsonResponse({"status": "ok", "entries": entries_data})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


