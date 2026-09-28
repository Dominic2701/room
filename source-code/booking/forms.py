from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Booking,
    GalleryImage,
    Payment,
    Profile,
    Residency,
    Room,
)


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        image_field = forms.ImageField()
        return [image_field.clean(image) for image in files]


class ResidencyForm(forms.ModelForm):
    gallery_images = MultipleImageField(required=False, label="Gallery images")

    class Meta:
        model = Residency
        fields = (
            "residency_name",
            "location",
            "address",
            "provider_name",
            "description",
            "phone",
            "email",
            "main_image",
            "status",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def save(self, commit=True):
        previous_storage = self.instance.main_image.storage
        previous_image = (
            self.instance.main_image.name
            if self.instance.pk and self.instance.main_image
            else None
        )
        residency = super().save(commit=commit)
        if commit:
            current_image = residency.main_image.name if residency.main_image else None
            if previous_image and previous_image != current_image:
                previous_storage.delete(previous_image)
            for uploaded_image in self.cleaned_data.get("gallery_images", []):
                GalleryImage.objects.create(
                    residency=residency,
                    image=uploaded_image,
                    image_type=GalleryImage.ImageType.OTHER,
                )
        return residency


class GalleryUploadForm(forms.Form):
    image_type = forms.ChoiceField(choices=GalleryImage.ImageType.choices)
    caption = forms.CharField(max_length=150, required=False)
    images = MultipleImageField(required=True, label="Choose images")


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
    number_of_rooms = forms.IntegerField(
        min_value=1, initial=1, required=False, label="Rooms"
    )
    payment_method = forms.ChoiceField(
        choices=Payment.Method.choices,
        initial=Payment.Method.GPAY,
        required=False,
        label="Payment method",
    )

    class Meta:
        model = Booking
        fields = ("check_in", "check_out", "guests", "number_of_rooms", "special_request")
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
        number_of_rooms = cleaned.get("number_of_rooms")
        if not number_of_rooms:
            cleaned["number_of_rooms"] = number_of_rooms = 1
        if check_in and check_in < timezone.localdate():
            self.add_error("check_in", "Check-in cannot be in the past.")
        if check_in and check_out and check_out <= check_in:
            self.add_error("check_out", "Check-out must be after check-in.")
        if guests and guests > self.room.capacity:
            self.add_error(
                "guests", f"This room accommodates up to {self.room.capacity} guests."
            )
        if number_of_rooms and number_of_rooms > self.room.available_rooms:
            raise forms.ValidationError(
                f"Only {self.room.available_rooms} rooms are currently available."
            )
        if self.room.total_rooms == 1 and check_in and check_out and check_out > check_in:
            conflict = Booking.objects.filter(
                room=self.room,
                booking_status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
            if self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError("This room is already booked for those dates.")
        if self.room.status != Room.Status.AVAILABLE:
            raise forms.ValidationError("This room is currently unavailable.")
        return cleaned


class RoomFilterForm(forms.Form):
    residency = forms.CharField(required=False, label="Residency")
    location = forms.CharField(required=False, label="Location")
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
    gallery_images = MultipleImageField(required=False, label="Gallery images")

    class Meta:
        model = Room
        fields = (
            "residency",
            "room_number",
            "room_type",
            "description",
            "price_per_night",
            "total_rooms",
            "available_rooms",
            "capacity",
            "floor",
            "amenities",
            "image",
            "status",
        )

    def __init__(self, *args, admin_account, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["residency"].queryset = admin_account.residencies.all()
        if not self.instance.pk and self.fields["residency"].queryset.count() == 1:
            self.fields["residency"].initial = self.fields["residency"].queryset.first()

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("total_rooms")
        available = cleaned.get("available_rooms")
        if total is not None and available is not None and available > total:
            raise forms.ValidationError("Available rooms cannot be greater than total rooms.")
        if self.instance.pk and total is not None and available is not None:
            reserved = (
                Booking.objects.filter(
                    room=self.instance,
                    booking_status__in=[
                        Booking.Status.PENDING,
                        Booking.Status.CONFIRMED,
                    ],
                ).aggregate(total=Sum("number_of_rooms"))["total"]
                or 0
            )
            if total < reserved or available > total - reserved:
                raise forms.ValidationError(
                    f"Inventory must account for {reserved} rooms already reserved."
                )
        residency = cleaned.get("residency")
        if (
            self.instance.pk
            and residency
            and residency.pk != self.instance.residency_id
            and Booking.objects.filter(room=self.instance).exists()
        ):
            self.add_error(
                "residency",
                "A room with booking history cannot be moved to another residency.",
            )
        return cleaned

    def save(self, commit=True):
        previous_storage = self.instance.image.storage
        previous_image = (
            self.instance.image.name
            if self.instance.pk and self.instance.image
            else None
        )
        room = super().save(commit=commit)
        if commit:
            current_image = room.image.name if room.image else None
            if previous_image and previous_image != current_image:
                previous_storage.delete(previous_image)
            for uploaded_image in self.cleaned_data.get("gallery_images", []):
                GalleryImage.objects.create(
                    room=room,
                    image=uploaded_image,
                    image_type=GalleryImage.ImageType.ROOM,
                )
        return room
