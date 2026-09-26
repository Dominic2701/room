from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("admin-register/", views.admin_register, name="admin_register"),
    path("admin-setup/", views.admin_setup, name="admin_setup"),
    path("logout/", views.logout_view, name="logout"),
    path("rooms/", views.room_list, name="room_list"),
    path("rooms/<int:pk>/", views.room_detail, name="room_detail"),
    path("book/<int:room_id>/", views.book_room, name="book_room"),
    path("payment/<int:pk>/", views.payment_checkout, name="payment_checkout"),
    path("booking/<int:pk>/", views.booking_detail, name="booking_detail"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("booking/<int:pk>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("booking/<int:pk>/receipt/", views.booking_receipt, name="booking_receipt"),
    path("profile/", views.profile, name="profile"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/rooms/", views.admin_rooms, name="admin_rooms"),
    path("admin-dashboard/rooms/add/", views.admin_room_add, name="admin_room_add"),
    path(
        "admin-dashboard/rooms/<int:pk>/edit/",
        views.admin_room_edit,
        name="admin_room_edit",
    ),
    path(
        "admin-dashboard/rooms/<int:pk>/delete/",
        views.admin_room_delete,
        name="admin_room_delete",
    ),
    path("admin-dashboard/bookings/", views.admin_bookings, name="admin_bookings"),
    path(
        "admin-dashboard/bookings/<int:pk>/<str:action>/",
        views.admin_booking_action,
        name="admin_booking_action",
    ),
    path("admin-dashboard/users/", views.admin_users, name="admin_users"),
    path("admin-dashboard/payments/", views.admin_payments, name="admin_payments"),
]
