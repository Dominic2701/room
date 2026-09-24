from io import BytesIO

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from .forms import BookingForm, ProfileForm, RegistrationForm, RoomFilterForm, RoomForm
from .models import Booking, Payment, Profile, Room


def home(request):
    featured_rooms = Room.objects.filter(status=Room.Status.AVAILABLE)[:3]
    return render(request, "home.html", {"featured_rooms": featured_rooms})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request, "Your account is ready. Find a room that fits your stay."
        )
        return redirect("room_list")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("admin_dashboard" if user.is_staff else "home")
        messages.error(request, "The username or password was not recognised.")
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


def room_list(request):
    form = RoomFilterForm(request.GET or None)
    rooms = Room.objects.filter(status=Room.Status.AVAILABLE)
    if form.is_valid():
        data = form.cleaned_data
        if data.get("room_type"):
            rooms = rooms.filter(room_type=data["room_type"])
        if data.get("min_price") is not None:
            rooms = rooms.filter(price_per_night__gte=data["min_price"])
        if data.get("max_price") is not None:
            rooms = rooms.filter(price_per_night__lte=data["max_price"])
        if data.get("capacity"):
            rooms = rooms.filter(capacity__gte=data["capacity"])
        if data.get("check_in") and data.get("check_out"):
            blocked = Booking.objects.filter(
                booking_status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                check_in__lt=data["check_out"],
                check_out__gt=data["check_in"],
            ).values_list("room_id", flat=True)
            rooms = rooms.exclude(id__in=blocked)
    return render(request, "rooms.html", {"rooms": rooms, "form": form})


def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, "room_detail.html", {"room": room})


@login_required
def book_room(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    form = BookingForm(request.POST or None, room=room)
    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.room = room
        booking.booking_status = Booking.Status.PENDING
        booking.save()
        Payment.objects.create(
            booking=booking,
            amount=booking.total_amount,
            payment_status=Payment.Status.PENDING,
            payment_method=form.cleaned_data["payment_method"],
        )
        return redirect("payment_checkout", pk=booking.pk)
    return render(request, "booking.html", {"room": room, "form": form})


def _owned_booking(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("room", "user"), pk=pk)
    if not request.user.is_staff and booking.user_id != request.user.id:
        raise Http404
    return booking


@login_required
def booking_detail(request, pk):
    booking = _owned_booking(request, pk)
    if booking.booking_status == Booking.Status.PENDING:
        return redirect("payment_checkout", pk=booking.pk)
    return render(request, "booking_detail.html", {"booking": booking})


@login_required
def payment_checkout(request, pk):
    booking = _owned_booking(request, pk)
    payment = get_object_or_404(Payment, booking=booking)
    if payment.payment_status == Payment.Status.SUCCESS:
        return redirect("booking_detail", pk=booking.pk)
    if request.method == "POST":
        payment.payment_status = Payment.Status.SUCCESS
        payment.transaction_id = f"DEMO-{booking.booking_id}"
        payment.save(update_fields=["payment_status", "transaction_id"])
        booking.booking_status = Booking.Status.CONFIRMED
        booking.save(update_fields=["booking_status"])
        messages.success(
            request, f"Payment successful. Booking {booking.booking_id} is confirmed."
        )
        return redirect("booking_detail", pk=booking.pk)
    payment_app_links = {
        Payment.Method.GPAY: "tez://upi/pay",
        Payment.Method.PHONEPE: "phonepe://pay",
        Payment.Method.PAYTM: "paytmmp://pay",
    }
    return render(
        request,
        "payment_checkout.html",
        {
            "booking": booking,
            "payment": payment,
            "payment_app_url": payment_app_links.get(payment.payment_method),
        },
    )


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related("room")
    return render(request, "my_bookings.html", {"bookings": bookings})


@login_required
def cancel_booking(request, pk):
    booking = _owned_booking(request, pk)
    if request.method == "POST":
        if booking.is_cancellable:
            booking.booking_status = Booking.Status.CANCELLED
            booking.save(update_fields=["booking_status"])
            Payment.objects.filter(
                booking=booking, payment_status=Payment.Status.SUCCESS
            ).update(payment_status=Payment.Status.REFUNDED)
            messages.success(request, "Booking cancelled successfully.")
        else:
            messages.error(request, "This booking can no longer be cancelled.")
        return redirect("my_bookings")
    return render(request, "cancel_booking.html", {"booking": booking})


@login_required
def booking_receipt(request, pk):
    booking = _owned_booking(request, pk)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    story = [Paragraph("ROOM BOOKING RECEIPT", styles["Title"]), Spacer(1, 8 * mm)]
    rows = [
        ["Booking ID", booking.booking_id],
        ["Customer", booking.user.get_full_name() or booking.user.username],
        ["Email", booking.user.email],
        [
            "Room",
            f"{booking.room.room_number} - {booking.room.get_room_type_display()}",
        ],
        ["Check-in", booking.check_in.strftime("%d %B %Y")],
        ["Check-out", booking.check_out.strftime("%d %B %Y")],
        ["Guests", str(booking.guests)],
        ["Nights", str(booking.number_of_nights)],
        ["Price per night", f"INR {booking.price_per_night:,.2f}"],
        ["Total", f"INR {booking.total_amount:,.2f}"],
        ["Status", booking.get_booking_status_display()],
        ["Booked on", booking.booking_date.strftime("%d %B %Y")],
    ]
    table = Table(rows, colWidths=[45 * mm, 115 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e9f1ed")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d4ce")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    document.build(story)
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"{booking.booking_id}.pdf",
        content_type="application/pdf",
    )


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(
        request.POST or None, request.FILES or None, instance=profile_obj
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("profile")
    return render(request, "profile.html", {"form": form})


def staff_required(view):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


@staff_required
def admin_dashboard(request):
    context = {
        "user_count": User.objects.count(),
        "room_count": Room.objects.count(),
        "available_rooms": Room.objects.filter(status=Room.Status.AVAILABLE).count(),
        "booking_count": Booking.objects.count(),
        "pending_count": Booking.objects.filter(
            booking_status=Booking.Status.PENDING
        ).count(),
        "confirmed_count": Booking.objects.filter(
            booking_status=Booking.Status.CONFIRMED
        ).count(),
        "cancelled_count": Booking.objects.filter(
            booking_status=Booking.Status.CANCELLED
        ).count(),
        "revenue": Booking.objects.filter(
            booking_status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0,
        "recent_bookings": Booking.objects.select_related("user", "room")[:6],
    }
    return render(request, "admin/dashboard.html", context)


@staff_required
def admin_rooms(request):
    return render(request, "admin/rooms.html", {"rooms": Room.objects.all()})


@staff_required
def admin_room_add(request):
    form = RoomForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room added.")
        return redirect("admin_rooms")
    return render(request, "admin/room_form.html", {"form": form, "title": "Add room"})


@staff_required
def admin_room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RoomForm(request.POST or None, request.FILES or None, instance=room)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room updated.")
        return redirect("admin_rooms")
    return render(
        request,
        "admin/room_form.html",
        {"form": form, "title": "Edit room", "room": room},
    )


@staff_required
def admin_room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == "POST":
        room.status = Room.Status.INACTIVE
        room.save(update_fields=["status"])
        messages.success(request, "Room marked inactive.")
    return redirect("admin_rooms")


@staff_required
def admin_bookings(request):
    bookings = Booking.objects.select_related("user", "room")
    return render(request, "admin/bookings.html", {"bookings": bookings})


@staff_required
def admin_booking_action(request, pk, action):
    booking = get_object_or_404(Booking, pk=pk)
    transitions = {
        "confirm": Booking.Status.CONFIRMED,
        "reject": Booking.Status.REJECTED,
        "cancel": Booking.Status.CANCELLED,
        "complete": Booking.Status.COMPLETED,
    }
    allowed_statuses = {
        "confirm": {Booking.Status.PENDING},
        "reject": {Booking.Status.PENDING},
        "cancel": {Booking.Status.PENDING, Booking.Status.CONFIRMED},
        "complete": {Booking.Status.CONFIRMED},
    }
    if (
        request.method == "POST"
        and action in transitions
        and booking.booking_status in allowed_statuses[action]
    ):
        booking.booking_status = transitions[action]
        booking.save(update_fields=["booking_status"])
        messages.success(
            request,
            f"Booking {booking.booking_id} marked {booking.get_booking_status_display().lower()}.",
        )
    return redirect("admin_bookings")


@staff_required
def admin_users(request):
    return render(
        request,
        "admin/users.html",
        {"users": User.objects.select_related("profile").order_by("-date_joined")},
    )


@staff_required
def admin_payments(request):
    return render(
        request,
        "admin/payments.html",
        {"payments": Payment.objects.select_related("booking", "booking__user")},
    )
