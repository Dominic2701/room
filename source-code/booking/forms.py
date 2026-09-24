from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Booking, Payment, Profile, Room


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "phone",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user, defaults={"phone": self.cleaned_data["phone"]}
            )
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "profile_image",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        profile.user.first_name = self.cleaned_data["first_name"]
        profile.user.last_name = self.cleaned_data["last_name"]
        profile.user.email = self.cleaned_data["email"]
        if commit:
            profile.user.save(update_fields=["first_name", "last_name", "email"])
        return profile


class BookingForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=Payment.Method.choices,
        initial=Payment.Method.GPAY,
        label="Payment method",
    )

    class Meta:
        model = Booking
        fields = ("check_in", "check_out", "guests", "special_request")
        widgets = {
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
            "special_request": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Anything we should prepare?"}
            ),
        }

    def __init__(self, *args, room, **kwargs):
        self.room = room
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        guests = cleaned.get("guests")
        if check_in and check_in < timezone.localdate():
            self.add_error("check_in", "Check-in cannot be in the past.")
        if check_in and check_out and check_out <= check_in:
            self.add_error("check_out", "Check-out must be after check-in.")
        if guests and guests > self.room.capacity:
            self.add_error(
                "guests", f"This room accommodates up to {self.room.capacity} guests."
            )
        if check_in and check_out and check_out > check_in:
            conflict = Booking.objects.filter(
                room=self.room,
                booking_status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
            if self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError(
                    "This room is already booked for those dates."
                )
        if self.room.status != Room.Status.AVAILABLE:
            raise forms.ValidationError("This room is currently unavailable.")
        return cleaned


class RoomFilterForm(forms.Form):
    room_type = forms.ChoiceField(
        choices=[("", "All room types"), *Room.RoomType.choices], required=False
    )
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
    capacity = forms.IntegerField(required=False, min_value=1)
    check_in = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    check_out = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("min_price")
            and cleaned.get("max_price")
            and cleaned["min_price"] > cleaned["max_price"]
        ):
            raise forms.ValidationError("Minimum price cannot exceed maximum price.")
        if (
            cleaned.get("check_in")
            and cleaned.get("check_out")
            and cleaned["check_out"] <= cleaned["check_in"]
        ):
            raise forms.ValidationError("Check-out must be after check-in.")
        return cleaned


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = (
            "room_number",
            "room_type",
            "description",
            "price_per_night",
            "capacity",
            "floor",
            "amenities",
            "image",
            "status",
        )
