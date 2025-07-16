from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VehicleEntry, Cars
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from asgiref.sync import sync_to_async

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
def receive_image(request):
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
                if car.is_free:
                    VehicleEntry.objects.create(number_plate=number_plate,
                    entry_image=request.FILES['entry_image'],
                    total_amount=0,
                    is_paid=True
                    )
                elif car.is_special_taxi:
                    today = timezone.now().date()
                    if VehicleEntry.objects.filter(number_plate=number_plate, entry_time__date=today).exists():
                        VehicleEntry.objects.create(number_plate=number_plate,
                        entry_image=request.FILES['entry_image'],
                        total_amount=0,
                        is_paid=True
                        )
                    else:
                        VehicleEntry.objects.create(number_plate=number_plate,
                        entry_image=request.FILES['entry_image'],
                        total_amount=0,
                        is_paid=False
                        )
                else:
                    VehicleEntry.objects.create(number_plate=number_plate,
                    entry_image=request.FILES['entry_image'],
                    total_amount=0,
                    is_paid=False
                    )

        print("================================\n")
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Only POST allowed"}, status=405)
