from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
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

from .forms import (
    BookingForm,
    GalleryUploadForm,
    ProfileForm,
    RegistrationForm,
    ResidencyForm,
    RoomFilterForm,
    RoomForm,
)
from .models import AdminAccount, Booking, GalleryImage, Payment, Profile, Residency, Room


def staff_required(view):
    def wrapped(request, *args, **kwargs):
        admin_id = request.session.get("admin_account_id")
        admin = AdminAccount.objects.filter(
            pk=admin_id, status=AdminAccount.Status.ACTIVE
        ).first()
        if not admin or not admin.residencies.exists():
            raise PermissionDenied
        request.admin_account = admin
        return view(request, *args, **kwargs)

    return wrapped


def _public_rooms():
    managed_residencies = Residency.objects.filter(
        status=Residency.Status.ACTIVE,
        admins__status=AdminAccount.Status.ACTIVE,
    ).values("pk")
    return Room.objects.filter(
        status=Room.Status.AVAILABLE,
        residency__status=Residency.Status.ACTIVE,
        residency_id__in=managed_residencies,
    )


def home(request):
    available_rooms = _public_rooms().filter(available_rooms__gt=0)
    featured_rooms = available_rooms.select_related(
        "residency"
    ).order_by("-residency__created_at")[:3]
    available_room_count = available_rooms.aggregate(
        total=Sum("available_rooms")
    )["total"] or 0
    return render(
        request,
        "home.html",
        {
            "featured_rooms": featured_rooms,
            "available_room_count": available_room_count,
        },
    )


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
            return redirect("home")
        messages.error(request, "The username or password was not recognised.")
    return render(request, "login.html")


def admin_login(request):
    if not AdminAccount.objects.filter(status=AdminAccount.Status.ACTIVE).exists():
        return redirect("admin_register")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        admin = AdminAccount.objects.filter(
            username=username, status=AdminAccount.Status.ACTIVE
        ).first()
        if admin and admin.verify_password(password):
            request.session.cycle_key()
            request.session["admin_account_id"] = admin.pk
            messages.success(request, "Admin login successful.")
            return redirect("admin_dashboard")
        messages.error(request, "Invalid admin username or password.")
    return render(request, "admin_login.html")


def admin_register(request):
    verified = request.session.get("developer_verified", False)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "verify":
            email = request.POST.get("developer_email", "").strip().lower()
            password = request.POST.get("developer_password", "")
            if not settings.DEVELOPER_PASSWORD_HASH:
                messages.error(
                    request,
                    "Developer verification is not configured. Run set_developer_password first.",
                )
            elif (
                email == settings.DEVELOPER_EMAIL.lower()
                and check_password(password, settings.DEVELOPER_PASSWORD_HASH)
            ):
                request.session["developer_verified"] = True
                verified = True
                messages.success(request, "Developer verification successful.")
            else:
                messages.error(request, "Invalid developer credentials.")
        elif action == "create" and verified:
            residency_name = request.POST.get("residency_name", "").strip()
            provider_name = request.POST.get("provider_name", "").strip()
            location = request.POST.get("location", "").strip()
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "")
            confirmation = request.POST.get("confirm_password", "")
            if not residency_name or not provider_name or not location or not username:
                messages.error(request, "Complete the residency and admin fields.")
            elif len(password) < 8 or password != confirmation:
                messages.error(request, "Enter matching admin passwords of at least 8 characters.")
            elif AdminAccount.objects.filter(username=username).exists():
                messages.error(request, "That admin username is already in use.")
            else:
                residency, _ = Residency.objects.get_or_create(
                    residency_name=residency_name,
                    defaults={"provider_name": provider_name, "location": location},
                )
                admin = AdminAccount.objects.create(
                    username=username,
                    password_hash=make_password(password),
                )
                admin.residencies.add(residency)
                request.session.pop("developer_verified", None)
                messages.success(request, "Admin account created successfully.")
                return redirect("admin_login")
    return render(request, "admin_setup.html", {"verified": verified})


def admin_setup(request):
    return redirect("admin_register")


@staff_required
def admin_residencies(request):
    residencies = request.admin_account.residencies.all().prefetch_related(
        "rooms", "gallery_images"
    )
    return render(
        request, "admin/residencies.html", {"residencies": residencies}
    )


@staff_required
def admin_residency_add(request):
    form = ResidencyForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        residency = form.save()
        request.admin_account.residencies.add(residency)
        messages.success(request, "Residency created successfully.")
        return redirect("admin_residencies")
    return render(
        request,
        "admin/residency_form.html",
        {"form": form, "title": "Add residency"},
    )


@staff_required
def admin_residency_edit(request, pk):
    residency = get_object_or_404(
        request.admin_account.residencies.all(), pk=pk
    )
    form = ResidencyForm(
        request.POST or None, request.FILES or None, instance=residency
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Residency updated successfully.")
        return redirect("admin_residencies")
    return render(
        request,
        "admin/residency_form.html",
        {"form": form, "title": "Edit residency", "residency": residency},
    )


@staff_required
def admin_residency_delete(request, pk):
    residency = get_object_or_404(
        request.admin_account.residencies.all(), pk=pk
    )
    if request.method == "POST":
        residency.status = Residency.Status.INACTIVE
        residency.save(update_fields=["status", "updated_at"])
        messages.success(request, "Residency has been deactivated.")
    return redirect("admin_residencies")


def _manage_gallery(request, *, parent, parent_kind):
    upload_form = GalleryUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and upload_form.is_valid():
        for image in upload_form.cleaned_data["images"]:
            GalleryImage.objects.create(
                **{parent_kind: parent},
                image=image,
                image_type=upload_form.cleaned_data["image_type"],
                caption=upload_form.cleaned_data["caption"],
            )
        messages.success(request, "Gallery images uploaded.")
        return redirect(request.path)

    return render(
        request,
        "admin/images.html",
        {
            "parent": parent,
            "parent_kind": parent_kind,
            "main_image": getattr(parent, "main_image", None)
            or getattr(parent, "image", None),
            "gallery_images": parent.gallery_images.all(),
            "upload_form": upload_form,
        },
    )


@staff_required
def admin_residency_images(request, pk):
    residency = get_object_or_404(
        request.admin_account.residencies.all(), pk=pk
    )
    return _manage_gallery(request, parent=residency, parent_kind="residency")


@staff_required
def admin_room_images(request, pk):
    room = get_object_or_404(
        Room.objects.filter(residency__in=request.admin_account.residencies.all()),
        pk=pk,
    )
    return _manage_gallery(request, parent=room, parent_kind="room")


@staff_required
def admin_gallery_image_delete(request, image_id):
    image = get_object_or_404(
        GalleryImage.objects.filter(
            Q(residency__in=request.admin_account.residencies.all())
            | Q(room__residency__in=request.admin_account.residencies.all())
        ),
        pk=image_id,
    )
    parent = image.residency or image.room
    parent_url = (
        "admin_residency_images"
        if image.residency_id
        else "admin_room_images"
    )
    if request.method == "POST":
        image.image.delete(save=False)
        image.delete()
        messages.success(request, "Gallery image deleted.")
    return redirect(parent_url, pk=parent.pk)


@staff_required
def admin_main_image_delete(request, parent_kind, pk):
    if parent_kind == "residency":
        parent = get_object_or_404(
            request.admin_account.residencies.all(), pk=pk
        )
        image_field = parent.main_image
        redirect_name = "admin_residency_images"
    elif parent_kind == "room":
        parent = get_object_or_404(
            Room.objects.filter(residency__in=request.admin_account.residencies.all()),
            pk=pk,
        )
        image_field = parent.image
        redirect_name = "admin_room_images"
    else:
        raise Http404
    if request.method == "POST" and image_field:
        image_field.delete(save=True)
        messages.success(request, "Main image deleted.")
    return redirect(redirect_name, pk=pk)


def logout_view(request):
    logout(request)
    request.session.pop("admin_account_id", None)
    request.session.pop("developer_verified", None)
    messages.info(request, "You have been signed out.")
    return redirect("home")


def room_list(request):
    form = RoomFilterForm(request.GET or None)
    rooms = _public_rooms().select_related("residency")
    if form.is_valid():
        data = form.cleaned_data
        if data.get("residency"):
            rooms = rooms.filter(residency__residency_name__icontains=data["residency"])
        if data.get("location"):
            rooms = rooms.filter(residency__location__icontains=data["location"])
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
                room__total_rooms=1,
                booking_status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                check_in__lt=data["check_out"],
                check_out__gt=data["check_in"],
            ).values_list("room_id", flat=True)
            rooms = rooms.exclude(id__in=blocked)
    residencies_without_rooms = (
        Residency.objects.filter(
            status=Residency.Status.ACTIVE,
            admins__status=AdminAccount.Status.ACTIVE,
        )
        .exclude(rooms__status=Room.Status.AVAILABLE)
        .distinct()
    )
    return render(
        request,
        "rooms.html",
        {
            "rooms": rooms,
            "form": form,
            "residencies_without_rooms": residencies_without_rooms,
        },
    )


def room_detail(request, pk):
    room = get_object_or_404(
        _public_rooms().select_related("residency").prefetch_related(
            "gallery_images", "residency__gallery_images"
        ),
        pk=pk,
    )
    return render(request, "room_detail.html", {"room": room})


@login_required
def book_room(request, room_id):
    room = get_object_or_404(_public_rooms(), pk=room_id)
    form = BookingForm(request.POST or None, room=room)
    if request.method == "POST" and form.is_valid():
        requested = form.cleaned_data["number_of_rooms"]
        with transaction.atomic():
            locked_room = Room.objects.select_for_update().get(pk=room.pk)
            if locked_room.status != Room.Status.AVAILABLE:
                form.add_error(None, "This room is currently unavailable.")
            elif requested > locked_room.available_rooms:
                form.add_error(
                    None, f"Only {locked_room.available_rooms} rooms are currently available."
                )
            else:
                locked_room.available_rooms -= requested
                locked_room.save(update_fields=["available_rooms", "updated_at"])
                booking = form.save(commit=False)
                booking.user = request.user
                booking.room = locked_room
                booking.number_of_rooms = requested
                booking.booking_status = Booking.Status.PENDING
                booking.save()
                Payment.objects.create(
                    booking=booking,
                    amount=booking.total_amount,
                    payment_status=Payment.Status.PENDING,
                    payment_method=form.cleaned_data["payment_method"] or Payment.Method.GPAY,
                )
                return redirect("payment_checkout", pk=booking.pk)
    return render(request, "booking.html", {"room": room, "form": form})


def _owned_booking(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("room", "user"), pk=pk)
    admin = getattr(request, "admin_account", None)
    if admin and not admin.residencies.filter(pk=booking.residency_id).exists():
        raise Http404
    if not admin and booking.user_id != request.user.id:
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
            with transaction.atomic():
                locked_room = Room.objects.select_for_update().get(pk=booking.room_id)
                locked_room.available_rooms = min(
                    locked_room.total_rooms,
                    locked_room.available_rooms + booking.number_of_rooms,
                )
                locked_room.save(update_fields=["available_rooms", "updated_at"])
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
        ["Rooms", str(booking.number_of_rooms)],
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


@staff_required
def admin_dashboard(request):
    residencies = request.admin_account.residencies.all()
    rooms = Room.objects.filter(residency__in=residencies)
    bookings = Booking.objects.filter(residency__in=residencies)
    context = {
        "residency": residencies.first(),
        "residencies": residencies,
        "user_count": bookings.values("user_id").distinct().count(),
        "room_count": rooms.count(),
        "total_rooms": rooms.aggregate(total=Sum("total_rooms"))["total"] or 0,
        "available_rooms": rooms.aggregate(total=Sum("available_rooms"))["total"] or 0,
        "booked_rooms": (rooms.aggregate(total=Sum("total_rooms"))["total"] or 0)
        - (rooms.aggregate(total=Sum("available_rooms"))["total"] or 0),
        "booking_count": bookings.count(),
        "pending_count": bookings.filter(
            booking_status=Booking.Status.PENDING
        ).count(),
        "confirmed_count": bookings.filter(
            booking_status=Booking.Status.CONFIRMED
        ).count(),
        "cancelled_count": bookings.filter(
            booking_status=Booking.Status.CANCELLED
        ).count(),
        "revenue": bookings.filter(
            booking_status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED]
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0,
        "recent_bookings": bookings.select_related("user", "room")[:6],
    }
    return render(request, "admin/dashboard.html", context)


@staff_required
def admin_rooms(request):
    return render(
        request,
        "admin/rooms.html",
        {
            "rooms": Room.objects.filter(
                residency__in=request.admin_account.residencies.all()
            ).select_related("residency")
        },
    )


@staff_required
def admin_room_add(request):
    form = RoomForm(
        request.POST or None,
        request.FILES or None,
        admin_account=request.admin_account,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room added.")
        return redirect("admin_rooms")
    return render(request, "admin/room_form.html", {"form": form, "title": "Add room"})


@staff_required
def admin_room_edit(request, pk):
    room = get_object_or_404(
        Room, pk=pk, residency__in=request.admin_account.residencies.all()
    )
    form = RoomForm(
        request.POST or None,
        request.FILES or None,
        instance=room,
        admin_account=request.admin_account,
    )
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
    room = get_object_or_404(
        Room, pk=pk, residency__in=request.admin_account.residencies.all()
    )
    if request.method == "POST":
        room.status = Room.Status.INACTIVE
        room.save(update_fields=["status"])
        messages.success(request, "Room marked inactive.")
    return redirect("admin_rooms")


@staff_required
def admin_bookings(request):
    bookings = Booking.objects.filter(
        residency__in=request.admin_account.residencies.all()
    ).select_related("user", "room")
    return render(request, "admin/bookings.html", {"bookings": bookings})


@staff_required
def admin_booking_action(request, pk, action):
    booking = get_object_or_404(
        Booking, pk=pk, residency__in=request.admin_account.residencies.all()
    )
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
        with transaction.atomic():
            if transitions[action] in {Booking.Status.REJECTED, Booking.Status.CANCELLED}:
                room = Room.objects.select_for_update().get(pk=booking.room_id)
                room.available_rooms = min(
                    room.total_rooms, room.available_rooms + booking.number_of_rooms
                )
                room.save(update_fields=["available_rooms", "updated_at"])
            booking.booking_status = transitions[action]
            booking.save(update_fields=["booking_status"])
        messages.success(
            request,
            f"Booking {booking.booking_id} marked {booking.get_booking_status_display().lower()}.",
        )
    return redirect("admin_bookings")


@staff_required
def admin_users(request):
    user_ids = Booking.objects.filter(
        residency__in=request.admin_account.residencies.all()
    ).values("user_id")
    return render(
        request,
        "admin/users.html",
        {"users": User.objects.filter(id__in=user_ids).select_related("profile").order_by("-date_joined")},
    )


@staff_required
def admin_payments(request):
    booking_ids = Booking.objects.filter(
        residency__in=request.admin_account.residencies.all()
    ).values("pk")
    return render(
        request,
        "admin/payments.html",
        {"payments": Payment.objects.filter(booking_id__in=booking_ids).select_related("booking", "booking__user")},
    )
