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
    
class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('login')


class HomeView(View):
    def get(self, request):
        return render(request, 'home.html')


@csrf_exempt
@sync_to_async
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
            car = Cars.objects.get_or_create(number_plate=number_plate)
            if car:
                if car.is_free and not car.is_blocked:
                    VehicleEntry.objects.create(number_plate=number_plate,
                    entry_image=request.FILES['entry_image'],
                    total_amount=0,
                    )
                elif car.is_special_taxi and not car.is_blocked:
                    today = timezone.now().date()
                    if VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).exists():
                        VehicleEntry.objects.create(number_plate=number_plate,
                        entry_image=request.FILES['entry_image'],
                        total_amount=0,
                        )
                    else:
                        VehicleEntry.objects.create(number_plate=number_plate,
                        entry_image=request.FILES['entry_image'],
                        total_amount=0,
                        )
                else:
                    if not car.is_blocked:
                        VehicleEntry.objects.create(number_plate=number_plate,
                        entry_image=request.FILES['entry_image'],
                        total_amount=0,
                        )

        print("================================\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Only POST allowed"}, status=405)

@csrf_exempt
@sync_to_async
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
            car = Cars.objects.get_or_create(number_plate=number_plate)
            today = timezone.now().date()
            if car:
                if car.is_free:
                    VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).last().update(
                    exit_image=request.FILES['exit_image'],
                    total_amount=0,
                    )
                elif car.is_special_taxi and not car.is_blocked:
                    if VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).exists():
                        VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).last().update(
                        exit_image=request.FILES['exit_image'],
                        total_amount=0,
                        )
                    else:
                        VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).last().update(
                        exit_image=request.FILES['exit_image'],
                        total_amount=(timezone.now()-F('entry_time'))*HOUR_PRICE,
                        )
                else:
                    if not car.is_blocked:
                        VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).last().update(
                        exit_image=request.FILES['exit_image'],
                        total_amount=(timezone.now()-F('entry_time'))*HOUR_PRICE,
                        )

        print("================================\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Only POST allowed"}, status=405)


