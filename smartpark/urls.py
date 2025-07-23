# urls.py
from django.urls import path
from .views import (
    receive_entry,
    receive_exit,
    LoginView,
    LogoutView,
    HomeView,
    get_statistics,
    get_vehicle_entries,
    mark_as_paid,
    add_car,
    block_car,
    get_unpaid_entries,
    get_receipt,
    FreePlateNumberView, 
    DeleteFreePlateView,
    CarsManagementView,
    create_car,
    update_car,
    delete_car,
    upload_license,
    UnpaidEntriesView
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

urlpatterns = (
    [
        path("", RedirectView.as_view(url="home/", permanent=True)),
        path("receive-entry/", receive_entry),
        path("receive-exit/", receive_exit),
        path("login/", LoginView.as_view(), name="login"),
        path("logout/", LogoutView.as_view(), name="logout"),
        path("home/", HomeView.as_view(), name="home"),
        # Cars management
        path("cars/", CarsManagementView.as_view(), name="cars_management"),
        path("api/cars/create/", create_car, name="create_car"),
        path("api/cars/<int:car_id>/update/", update_car, name="update_car"),
        path("api/cars/<int:car_id>/delete/", delete_car, name="delete_car"),
        path("api/cars/upload-license/", upload_license, name="upload_license"),
        # New API endpoints
        path("api/statistics/", get_statistics, name="get_statistics"),
        path("api/vehicle-entries/", get_vehicle_entries, name="get_vehicle_entries"),
        path("api/mark-paid/", mark_as_paid, name="mark_as_paid"),
        path("api/add-car/", add_car, name="add_car"),
        path("api/block-car/", block_car, name="block_car"),
        path("api/unpaid-entries/", get_unpaid_entries, name="get_unpaid_entries"),
        path("api/receipt/", get_receipt, name="get_receipt"),
        path('free-plate-number/', FreePlateNumberView.as_view(), name='free_plate_number'),
        path('delete-free-plate/<int:pk>/', DeleteFreePlateView.as_view(), name='delete_free_plate'),
        path('unpaid-entries/', UnpaidEntriesView.as_view(), name='unpaid_entries'),

    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + staticfiles_urlpatterns()
)
