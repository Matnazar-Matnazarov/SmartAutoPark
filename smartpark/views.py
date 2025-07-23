from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VehicleEntry, Cars
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from datetime import datetime, timedelta
import re
from django.core.files.base import ContentFile
from django.db import transaction
from django.views.decorators.http import require_POST, require_GET
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from config.settings import MIN_TIME_BETWEEN_ENTRIES

class LoginView(View):
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            return render(
                request,
                "login.html",
                {
                    "message": "Login yoki parol xato. Iltimos tekshirib qayta urinib ko`ring!"
                },
                status=401,
            )


class LogoutView(LoginRequiredMixin, View):
    def post(self, request):
        logout(request)
        return redirect("login")
    
    def get(self, request):
        logout(request)
        return redirect("login")


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "home.html")


@csrf_exempt
@require_POST
def receive_entry(request):
    try:
        with transaction.atomic():
            content_type = request.headers.get("Content-Type", "")
            body_bytes = request.body
            body_str = body_bytes.decode("utf-8", errors="ignore")

            # 1. XML'dan davlat raqamini ajratamiz (masalan <licensePlate> tagidan)
            number_plate_match = re.search(
                r"<licensePlate>(.*?)</licensePlate>", body_str
            )
            number_plate = (
                number_plate_match.group(1)
                if number_plate_match
                else f"TEMP{timezone.now().strftime('%H%M%S')}"
            )

            # 2. Faylni multipart dan ajratish
            # Bu oddiy variant: multipart so'rovdan rasmni olish
            boundary = (
                content_type.split("boundary=")[-1]
                if "boundary=" in content_type
                else None
            )

            if boundary:
                parts = body_bytes.split(boundary.encode())
                image_data = None
                for part in parts:
                    if b"Content-Type: image/jpeg" in part:
                        image_data = part.split(b"\r\n\r\n", 1)[-1].rsplit(b"\r\n", 1)[
                            0
                        ]
                        break
                car = Cars.objects.filter(number_plate=number_plate, is_blocked=True).first()
                if car:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                                "home_updates",
                                {
                                    "type": "broadcast_notification",
                                    "title": "🚫 Bloklangan avtomobil",
                                    "message": f"Avtomobil {number_plate} bloklangan! Chiqish taqiqlanadi.",
                                    "notification_type": "error",
                                    "timestamp": timezone.now().isoformat(),
                                },
                            )
                            
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"Bu avtomobilga taqiq qo'shilgan! {number_plate}",
                        }
                    )
                if image_data:
                    # 3. Fayl nomi: Raqam + sana (20250717_135501.jpg)
                    current_time = timezone.now()
                    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
                    filename = f"{number_plate}_{timestamp}.jpg"

                    # 4. Rasmdan ImageField fayl obyektini yasaymiz
                    image_file = ContentFile(image_data, name=filename)

                    # 5. Bazaga yozamiz - entry_time auto_now_add=True bo'lgani uchun o'rnatmaymiz
                    if VehicleEntry.objects.filter(number_plate=number_plate, exit_time__isnull=True).exists():
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                                    "home_updates",
                                    {
                                        "type": "broadcast_notification",
                                        "title": "🚫 Avtomobil oldin kiritilgan",
                                        "message": f"Avtomobil {number_plate} oldin kiritilgan!",
                                        "notification_type": "warning",
                                        "timestamp": timezone.now().isoformat(),
                                    },
                                )
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": f"Bu avtomobilga taqiq qo'shilgan! {number_plate}",
                            }
                        )
                    entry = VehicleEntry.objects.create(
                        number_plate=number_plate,
                        entry_image=image_file,
                        total_amount=0,
                    )

                    return JsonResponse(
                        {
                            "status": "ok",
                            "message": "VehicleEntry created",
                            "number_plate": number_plate,
                            "file_saved": filename,
                            "entry_id": entry.id,
                        }
                    )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def receive_exit(request):
    try:
        with transaction.atomic():
            content_type = request.headers.get("Content-Type", "")
            body_bytes = request.body
            body_str = body_bytes.decode("utf-8", errors="ignore")
            current_time = timezone.now()

            # Create timezone-aware datetime range for today
            today = current_time.date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

            # 1. XML'dan davlat raqamini ajratamiz (masalan <licensePlate> tagidan)
            number_plate_match = re.search(
                r"<licensePlate>(.*?)</licensePlate>", body_str
            )
            number_plate = (
                number_plate_match.group(1)
                if number_plate_match
                else f"TEMP{current_time.strftime('%H%M%S')}"
            )
            car = Cars.objects.filter(number_plate=number_plate).first()

            # 2. Faylni multipart dan ajratish
            # Bu oddiy variant: multipart so'rovdan rasmni olish
            boundary = (
                content_type.split("boundary=")[-1]
                if "boundary=" in content_type
                else None
            )

            if boundary:
                parts = body_bytes.split(boundary.encode())
                image_data = None
                for part in parts:
                    if b"Content-Type: image/jpeg" in part:
                        image_data = part.split(b"\r\n\r\n", 1)[-1].rsplit(b"\r\n", 1)[
                            0
                        ]
                        break

                if image_data:
                    # 3. Fayl nomi: Raqam + sana (20250717_135501.jpg)
                    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
                    filename = f"{number_plate}_{timestamp}.jpg"

                    # 4. Rasmdan ImageField fayl obyektini yasaymiz
                    image_file = ContentFile(image_data, name=filename)

                    # Use timezone-aware datetime range instead of naive date
                    latest_entry = (
                        VehicleEntry.objects.filter(
                            number_plate=number_plate,
                            entry_time__gte=start_datetime,
                            entry_time__lte=end_datetime,
                        )
                        .order_by("-entry_time")
                        .first()
                    )
                    if timezone.now() - latest_entry.entry_time <= timedelta(minutes=MIN_TIME_BETWEEN_ENTRIES):
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            "home_updates",
                            {
                                "type": "broadcast_notification",
                                "title": "🚫 Avtomobil oldin kiritilgan",
                                "message": f"Avtomobil {number_plate} oldin kiritilgan!",
                                "notification_type": "warning",
                                "timestamp": timezone.now().isoformat(),
                            },
                        )
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": f"Avtomobil {number_plate} oldin kiritilgan!",
                            }
                        )

                    if latest_entry and not latest_entry.exit_time:
                        # Check if car is blocked
                        if car and car.is_blocked:
                            # Send real-time notification about blocked car
                            
                            channel_layer = get_channel_layer()
                            async_to_sync(channel_layer.group_send)(
                                "home_updates",
                                {
                                    "type": "broadcast_notification",
                                    "title": "🚫 Bloklangan avtomobil",
                                    "message": f"Avtomobil {number_plate} bloklangan! Chiqish taqiqlanadi.",
                                    "notification_type": "error",
                                    "timestamp": timezone.now().isoformat(),
                                },
                            )
                            
                            return JsonResponse(
                                {
                                    "status": "error",
                                    "message": f"Bu avtomobilga taqiq qo'shilgan! {number_plate}",
                                }
                            )
                        
                        if car and car.is_free and not car.is_blocked:
                            latest_entry.exit_image = image_file
                            latest_entry.total_amount = 0
                            latest_entry.exit_time = current_time
                            latest_entry.save()
                        elif car and car.is_special_taxi and not car.is_blocked:
                            latest_entry.exit_image = image_file
                            latest_entry.total_amount = (
                                latest_entry.calculate_amount()
                                if VehicleEntry.objects.filter(
                                    entry_time__gte=start_datetime,
                                    entry_time__lte=end_datetime,
                                    number_plate=number_plate,
                                ).count()
                                < 2
                                else 0
                            )
                            latest_entry.exit_time = current_time
                            latest_entry.save()
                        else:
                            if (car and not car.is_blocked) or not car:
                                latest_entry.exit_image = image_file
                                latest_entry.exit_time = current_time
                                latest_entry.total_amount = (
                                    latest_entry.calculate_amount()
                                )
                                latest_entry.save()

                                

                        return JsonResponse(
                            {
                                "status": "ok",
                                "number_plate": number_plate,
                                "amount": latest_entry.total_amount,
                            }
                        )
                    else:
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                                "home_updates",
                                {
                                    "type": "broadcast_notification",
                                    "title": "🚫 Avtomobil bilan kirish bo'lmagan",
                                    "message": f"Avtomobil {number_plate} bilan kirish bo'lmagan!",
                                    "notification_type": "error",
                                    "timestamp": timezone.now().isoformat(),
                                },
                            )
                        return JsonResponse(
                            {"error": "Avtomobil bilan kirish bo'lmagan"}, status=404
                        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# New API endpoints for WebSocket functionality


@csrf_exempt
@require_GET
def get_statistics(request):
    """Get statistics for a specific date"""
    date_str = request.GET.get("date", timezone.now().date().isoformat())
    try:
        # Convert date string to timezone-aware datetime for proper filtering
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Create timezone-aware datetime range for the entire day
        start_datetime = timezone.make_aware(
            datetime.combine(date_obj, datetime.min.time())
        )
        end_datetime = timezone.make_aware(
            datetime.combine(date_obj, datetime.max.time())
        )
    except ValueError:
        # Fallback to today if date parsing fails
        today = timezone.now().date()
        start_datetime = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        )
        end_datetime = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    # Use timezone-aware datetime range instead of naive date
    today_entries = VehicleEntry.objects.filter(
        entry_time__gte=start_datetime, entry_time__lte=end_datetime
    )
    total_entries = today_entries.count()
    total_exits = today_entries.filter(exit_time__isnull=False).count()
    total_inside = total_entries - total_exits
    unpaid_entries = today_entries.filter(
        is_paid=False, exit_time__isnull=False
    ).count()

    return JsonResponse(
        {
            "total_entries": total_entries,
            "total_exits": total_exits,
            "total_inside": total_inside,
            "unpaid_entries": unpaid_entries,
        }
    )


@csrf_exempt
@require_GET
def get_vehicle_entries(request):
    """Get vehicle entries for a specific date with filters"""
    try:
        date_str = request.GET.get("date", timezone.now().date().isoformat())
        number_plate_filter = request.GET.get("number_plate", "")
        status_filter = request.GET.get(
            "status", "all"
        )  # all, paid, unpaid, inside, exited

        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Use timezone-aware datetime range instead of naive date
        entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime, entry_time__lte=end_datetime
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
            entry_time = (
                timezone.localtime(entry.entry_time)
                if timezone.is_naive(entry.entry_time)
                else entry.entry_time
            )
            exit_time = (
                timezone.localtime(entry.exit_time)
                if entry.exit_time and timezone.is_naive(entry.exit_time)
                else entry.exit_time
            )

            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M") if exit_time else None,
                    "total_amount": entry.total_amount or 0,
                    "is_paid": entry.is_paid,
                    "entry_image": entry.entry_image.url if entry.entry_image else None,
                    "exit_image": entry.exit_image.url if entry.exit_image else None,
                    "status": "inside"
                    if not entry.exit_time
                    else ("paid" if entry.is_paid else "unpaid"),
                }
            )

        return JsonResponse({"status": "ok", "entries": entries_data})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_POST
def mark_as_paid(request):
    """Mark a vehicle entry as paid"""
    try:
        data = json.loads(request.body)
        entry_id = data.get("entry_id")

        entry = VehicleEntry.objects.get(id=entry_id)
        entry.is_paid = True
        entry.save()

        return JsonResponse({"success": True, "entry_id": entry_id})
    except VehicleEntry.DoesNotExist:
        return JsonResponse({"success": False, "error": "Entry not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_POST
def add_car(request):
    """Add or update a car with boolean flags"""
    try:
        data = json.loads(request.body)
        number_plate = data.get("number_plate")
        car_type = data.get("car_type", "")  # "free", "special_taxi", "blocked", "normal"
        position = data.get("position", "")
        is_blocked = data.get("is_blocked", False)

        if not number_plate:
            return JsonResponse(
                {"success": False, "error": "Number plate is required"}, status=400
            )

        # Set flags based on car type
        is_free = car_type == "free"
        is_special_taxi = car_type == "special_taxi"
        is_blocked = car_type == "blocked" or is_blocked

        # Validate position for free cars
        if is_free and not position:
            return JsonResponse(
                {"success": False, "error": "Bepul avtomobillar uchun lavozim kiritish majburiy"}, status=400
            )

        car, created = Cars.objects.get_or_create(
            number_plate=number_plate,
            defaults={
                "is_free": is_free,
                "is_special_taxi": is_special_taxi,
                "is_blocked": is_blocked,
                "position": position if is_free else None,
            },
        )

        if not created:
            car.is_free = is_free
            car.is_special_taxi = is_special_taxi
            car.is_blocked = is_blocked
            car.position = position if is_free else None
            car.save()

        return JsonResponse(
            {
                "success": True,
                "car": {
                    "number_plate": car.number_plate,
                    "is_free": car.is_free,
                    "is_special_taxi": car.is_special_taxi,
                    "is_blocked": car.is_blocked,
                    "position": car.position,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_POST
def block_car(request):
    """Block a car by number plate"""
    try:
        data = json.loads(request.body)
        number_plate = data.get("number_plate")

        if not number_plate:
            return JsonResponse(
                {"success": False, "error": "Number plate is required"}, status=400
            )

        car = Cars.objects.get(number_plate=number_plate)
        car.is_blocked = True
        car.save()

        return JsonResponse({"success": True, "number_plate": number_plate})
    except Cars.DoesNotExist:
        return JsonResponse({"success": False, "error": "Car not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_GET
def get_unpaid_entries(request):
    """Get unpaid entries for receipt printing"""
    try:
        date_str = request.GET.get("date", timezone.now().date().isoformat())

        try:
            # Convert date string to timezone-aware datetime for proper filtering
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Create timezone-aware datetime range for the entire day
            start_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(date_obj, datetime.max.time())
            )
        except ValueError:
            # Fallback to today if date parsing fails
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, datetime.max.time())
            )

        # Get unpaid entries that have exited using timezone-aware datetime range
        unpaid_entries = VehicleEntry.objects.filter(
            entry_time__gte=start_datetime,
            entry_time__lte=end_datetime,
            is_paid=False,
            exit_time__isnull=False,
        ).order_by("-exit_time")

        entries_data = []
        for entry in unpaid_entries:
            # Ensure timezone-aware formatting
            entry_time = entry.entry_time
            exit_time = entry.exit_time

            entries_data.append(
                {
                    "id": entry.id,
                    "number_plate": entry.number_plate,
                    "entry_time": entry_time.strftime("%H:%M"),
                    "exit_time": exit_time.strftime("%H:%M"),
                    "total_amount": entry.total_amount or 0,
                    "duration_hours": (exit_time - entry_time).total_seconds() / 3600,
                }
            )

        return JsonResponse({"status": "ok", "entries": entries_data})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


class FreePlateNumberView(LoginRequiredMixin, View):
    def get(self, request):
        free_plates = Cars.objects.filter(is_free=True)
        return render(request, "freeplatenumber.html", {"free_plates": free_plates})

    def post(self, request):
        number_plate = request.POST.get("number_plate")

        if Cars.objects.filter(number_plate=number_plate).exists():
            return JsonResponse(
                {"success": False, "message": "Bu raqamli avtomobil allaqachon mavjud"},
                status=400,
            )
        else:
            Cars.objects.create(number_plate=number_plate, is_free=True)
            return JsonResponse(
                {"success": True, "message": "Avtomobil muvaffaqiyatli qo`shildi"},
                status=200,
            )


class DeleteFreePlateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        Cars.objects.filter(pk=pk).delete()
        return JsonResponse(
            {"success": True, "message": "Avtomobil muvaffaqiyatli o`chirildi"},
            status=200,
        )


@csrf_exempt
@require_GET
def get_receipt(request):
    """Get receipt data for a specific entry"""
    try:
        entry_id = request.GET.get("entry_id")
        if not entry_id:
            return JsonResponse({"error": "Entry ID is required"}, status=400)

        entry = VehicleEntry.objects.get(id=entry_id)

        if not entry.is_paid:
            return JsonResponse({"error": "Entry is not paid"}, status=400)

        # Ensure timezone-aware formatting
        entry_time = entry.entry_time
        exit_time = entry.exit_time

        receipt_data = {
            "id": entry.id,
            "number_plate": entry.number_plate,
            "entry_time": entry_time.strftime("%H:%M"),
            "exit_time": exit_time.strftime("%H:%M") if exit_time else None,
            "total_amount": entry.total_amount or 0,
            "is_paid": entry.is_paid,
            "duration_hours": (exit_time - entry_time).total_seconds() / 3600
            if exit_time
            else 0,
        }

        return JsonResponse({"status": "ok", "receipt": receipt_data})

    except VehicleEntry.DoesNotExist:
        return JsonResponse({"error": "Entry not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


class CarsManagementView(LoginRequiredMixin, View):
    def get(self, request):
        cars = Cars.objects.all().order_by("-id")

        # Calculate stats
        total_cars = cars.count()
        free_cars = cars.filter(is_free=True).count()
        special_taxi = cars.filter(is_special_taxi=True).count()
        blocked_cars = cars.filter(is_blocked=True).count()

        context = {
            "cars": cars,
            "total_cars": total_cars,
            "free_cars": free_cars,
            "special_taxi": special_taxi,
            "blocked_cars": blocked_cars,
        }
        return render(request, "cars_management.html", context)


@csrf_exempt
@require_POST
def create_car(request):
    """Create a new car"""
    try:
        data = json.loads(request.body)
        number_plate = data.get("number_plate")
        car_type = data.get("car_type", "")  # "free", "special_taxi", "blocked", "normal"
        position = data.get("position", "")
        is_blocked = data.get("is_blocked", False)

        if not number_plate:
            return JsonResponse(
                {"success": False, "error": "Number plate is required"}, status=400
            )

        # Check if car already exists
        if Cars.objects.filter(number_plate=number_plate).exists():
            return JsonResponse(
                {"success": False, "error": "Bu raqamli avtomobil allaqachon mavjud"},
                status=400,
            )

        # Set flags based on car type
        is_free = car_type == "free"
        is_special_taxi = car_type == "special_taxi"
        is_blocked = car_type == "blocked" or is_blocked

        # Validate position for free cars
        if is_free and not position:
            return JsonResponse(
                {"success": False, "error": "Bepul avtomobillar uchun lavozim kiritish majburiy"}, status=400
            )

        car = Cars.objects.create(
            number_plate=number_plate,
            is_free=is_free,
            is_special_taxi=is_special_taxi,
            is_blocked=is_blocked,
            position=position if is_free else None,
        )

        return JsonResponse(
            {
                "success": True,
                "car": {
                    "id": car.id,
                    "number_plate": car.number_plate,
                    "is_free": car.is_free,
                    "is_special_taxi": car.is_special_taxi,
                    "is_blocked": car.is_blocked,
                    "position": car.position,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_POST
def update_car(request, car_id):
    """Update an existing car"""
    try:
        data = json.loads(request.body)
        car_type = data.get("car_type", "")  # "free", "special_taxi", "blocked", "normal"
        position = data.get("position", "")
        is_blocked = data.get("is_blocked", False)

        car = Cars.objects.get(id=car_id)
        
        # Set flags based on car type
        car.is_free = car_type == "free"
        car.is_special_taxi = car_type == "special_taxi"
        car.is_blocked = car_type == "blocked" or is_blocked
        
        # Validate position for free cars
        if car_type == "free" and not position:
            return JsonResponse(
                {"success": False, "error": "Bepul avtomobillar uchun lavozim kiritish majburiy"}, status=400
            )
        
        car.position = position if car_type == "free" else None
        car.save()

        return JsonResponse(
            {
                "success": True,
                "car": {
                    "id": car.id,
                    "number_plate": car.number_plate,
                    "is_free": car.is_free,
                    "is_special_taxi": car.is_special_taxi,
                    "is_blocked": car.is_blocked,
                    "position": car.position,
                },
            }
        )
    except Cars.DoesNotExist:
        return JsonResponse({"success": False, "error": "Car not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_POST
def delete_car(request, car_id):
    """Delete a car"""
    try:
        car = Cars.objects.get(id=car_id)
        car.delete()
        return JsonResponse({"success": True, "car_id": car_id})
    except Cars.DoesNotExist:
        return JsonResponse({"success": False, "error": "Car not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@csrf_exempt
@require_POST
def upload_license(request):
    """Upload license file for special taxi"""
    try:
        if 'license_file' not in request.FILES:
            return JsonResponse({"success": False, "error": "Fayl yuklanmadi"}, status=400)
        
        license_file = request.FILES['license_file']
        car_id = request.POST.get('car_id')
        
        if not car_id:
            return JsonResponse({"success": False, "error": "Avtomobil ID kerak"}, status=400)
        
        car = Cars.objects.get(id=car_id)
        car.license_file = license_file
        car.save()
        
        return JsonResponse({
            "success": True,
            "license_url": car.license_file.url if car.license_file else None
        })
    except Cars.DoesNotExist:
        return JsonResponse({"success": False, "error": "Avtomobil topilmadi"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


class UnpaidEntriesView(LoginRequiredMixin, View):
    def get(self, request):
            return render(request, "unpaid_entries.html")
