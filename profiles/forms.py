from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from marketplace.models import Pharmacy
from .models import AccountDeletionRequest, CustomerAddress, ProfilePreferences

User = get_user_model()


class AccountDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This email address is already associated with another account.")
        return email


class ProfilePersonalForm(forms.ModelForm):
    class Meta:
        model = ProfilePreferences
        fields = ("contact_phone", "date_of_birth", "avatar")
        widgets = {
            "contact_phone": forms.TelInput(attrs={"class": "form-control", "autocomplete": "tel", "placeholder": "+91 …"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar or not hasattr(avatar, "read"):
            return avatar
        if avatar.size > 2 * 1024 * 1024:
            raise ValidationError("Profile pictures must be 2 MB or smaller.")
        ext = avatar.name.rsplit(".", 1)[-1].lower() if "." in avatar.name else ""
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            raise ValidationError("Upload a JPG, PNG or WebP image.")
        try:
            avatar.seek(0)
            image = Image.open(avatar)
            image.verify()
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError("The uploaded file is not a supported image.")
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise ValidationError("The uploaded file is not a valid image.")
        finally:
            avatar.seek(0)
        return avatar


class ProfilePreferencesForm(forms.ModelForm):
    class Meta:
        model = ProfilePreferences
        fields = ("preferred_language", "preferred_fulfilment", "notify_order_updates", "notify_prescription_updates", "notify_inventory_alerts", "notify_promotions")
        widgets = {
            "preferred_language": forms.Select(attrs={"class": "form-select"}),
            "preferred_fulfilment": forms.Select(attrs={"class": "form-select"}),
            "notify_order_updates": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_prescription_updates": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_inventory_alerts": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_promotions": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CustomerAddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = ("recipient_name", "phone", "address_line1", "locality", "city", "state", "pincode", "address_type", "is_default")
        widgets = {
            "recipient_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}),
            "phone": forms.TelInput(attrs={"class": "form-control", "autocomplete": "tel"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-line1"}),
            "locality": forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-line2"}),
            "city": forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-level2"}),
            "state": forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-level1"}),
            "pincode": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric", "autocomplete": "postal-code", "maxlength": "10"}),
            "address_type": forms.Select(attrs={"class": "form-select"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_pincode(self):
        value = (self.cleaned_data.get("pincode") or "").strip()
        if not value.isdigit() or not 4 <= len(value) <= 10:
            raise ValidationError("Enter a numeric PIN/postal code between 4 and 10 digits.")
        return value


class PharmacyBusinessForm(forms.ModelForm):
    class Meta:
        model = Pharmacy
        fields = (
            "name", "phone", "email", "address", "locality", "city", "state", "pincode",
            "opening_time", "closing_time", "offers_delivery", "offers_pickup", "delivery_fee",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TelInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "locality": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pincode": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
            "opening_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
            "closing_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}, format="%H:%M"),
            "offers_delivery": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "offers_pickup": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "delivery_fee": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("opening_time") and cleaned.get("closing_time") and cleaned["opening_time"] == cleaned["closing_time"]:
            self.add_error("closing_time", "Opening and closing times cannot be identical.")
        if not cleaned.get("offers_delivery") and not cleaned.get("offers_pickup"):
            raise ValidationError("Enable delivery, pickup, or both.")
        return cleaned


class DeletionRequestForm(forms.ModelForm):
    confirm = forms.BooleanField(required=True, label="I understand that this submits a request for review and does not immediately delete my account.", widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    class Meta:
        model = AccountDeletionRequest
        fields = ("reason",)
        widgets = {"reason": forms.Textarea(attrs={"class": "form-control", "rows": 3, "maxlength": 300})}
