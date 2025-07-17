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
            return JsonResponse({'error': 'Login yoki parol xato. Iltimos tekshirib qayta urinib ko`ring!'}, status=401)
    
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
        from pprint import pprint
        print("\n========== POST keldi ==========")
        print("Headers:")
        pprint(dict(request.headers))
        print("\nBody (bytes, first 100):")
        print(request.body)
        number_plate = request.POST.get('number_plate')
        print("Number Plate:", number_plate)
        
        if number_plate:
            try:
                # Fix: get_or_create returns a tuple (object, created)
                car, created = Cars.objects.get_or_create(number_plate=number_plate)
                
                if car.is_free and not car.is_blocked:
                    VehicleEntry.objects.create(
                        number_plate=number_plate,
                        entry_image=request.FILES.get('entry_image'),
                        total_amount=0,
                    )
                elif car.is_special_taxi and not car.is_blocked:
                    today = timezone.now().date()
                    if VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).exists():
                        VehicleEntry.objects.create(
                            number_plate=number_plate,
                            entry_image=request.FILES.get('entry_image'),
                            total_amount=0,
                        )
                    else:
                        VehicleEntry.objects.create(
                            number_plate=number_plate,
                            entry_image=request.FILES.get('entry_image'),
                            total_amount=0,
                        )
                else:
                    if not car.is_blocked:
                        VehicleEntry.objects.create(
                            number_plate=number_plate,
                            entry_image=request.FILES.get('entry_image'),
                            total_amount=0,
                        )
                
                print("Vehicle entry created successfully")
            except Exception as e:
                print(f"Error creating vehicle entry: {e}")
                return JsonResponse({"error": str(e)}, status=500)

        print("================================\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Only POST allowed"}, status=405)

@csrf_exempt
def receive_exit(request):
    if request.method == "POST":
        from pprint import pprint
        print("\n========== POST keldi ==========")
        print("Headers:")
        pprint(dict(request.headers))
        print("\nBody (bytes, first 100):")
        print(request.body)
        number_plate = request.POST.get('number_plate')
        print("Number Plate:", number_plate)
        
        if number_plate:
            try:
                # Fix: get_or_create returns a tuple (object, created)
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
                    
                    print("Vehicle exit updated successfully")
                else:
                    print("No entry found for this car today")
                    return JsonResponse({"error": "No entry found for this car today"}, status=404)
                    
            except Exception as e:
                print(f"Error updating vehicle exit: {e}")
                return JsonResponse({"error": str(e)}, status=500)

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


