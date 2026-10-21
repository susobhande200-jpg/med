from django import forms
from django.core.exceptions import ValidationError

from .models import Pharmacy, PharmacyListing, Prescription, CartItem, MarketplaceOrder


class PharmacyRegistrationForm(forms.ModelForm):
    class Meta:
        model = Pharmacy
        fields = [
            "name", "phone", "email", "address", "locality", "city", "state", "pincode",
            "latitude", "longitude", "licence_number", "licence_expiry", "pharmacist_name",
            "pharmacist_registration", "opening_time", "closing_time", "offers_delivery",
            "offers_pickup", "delivery_fee",
        ]
        widgets = {
            "licence_expiry": forms.DateInput(attrs={"type": "date"}),
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
            "latitude": forms.NumberInput(attrs={"step": "any", "placeholder": "Optional"}),
            "longitude": forms.NumberInput(attrs={"step": "any", "placeholder": "Optional"}),
            "offers_delivery": forms.CheckboxInput(),
            "offers_pickup": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-control"
            else:
                field.widget.attrs["class"] = "form-check-input"
        self.fields["name"].help_text = "Your store remains hidden from customers until an administrator verifies it."
        for required_field in ("licence_number", "licence_expiry", "pharmacist_name", "pharmacist_registration"):
            self.fields[required_field].required = True

    def clean_pincode(self):
        value = self.cleaned_data["pincode"].strip()
        if not value.isdigit() or not 4 <= len(value) <= 10:
            raise ValidationError("Enter a valid postal / PIN code.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("delivery_fee") is not None and cleaned["delivery_fee"] < 0:
            self.add_error("delivery_fee", "Delivery fee cannot be negative.")
        if cleaned.get("opening_time") and cleaned.get("closing_time") and cleaned["opening_time"] == cleaned["closing_time"]:
            self.add_error("closing_time", "Opening and closing time cannot be the same.")
        if not cleaned.get("offers_delivery") and not cleaned.get("offers_pickup"):
            raise ValidationError("Enable at least one fulfilment option: delivery or pickup.")
        return cleaned


class ListingForm(forms.ModelForm):
    class Meta:
        model = PharmacyListing
        fields = ["product", "mrp", "selling_price", "available_quantity", "batch_number", "expiry_date", "active"]
        widgets = {"expiry_date": forms.DateInput(attrs={"type": "date"}), "active": forms.CheckboxInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "active":
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"
        from .models import MedicineProduct
        self.fields["product"].queryset = MedicineProduct.objects.filter(active=True).order_by("brand_name", "strength")

    def clean(self):
        cleaned = super().clean()
        mrp, selling_price = cleaned.get("mrp"), cleaned.get("selling_price")
        if mrp is not None and selling_price is not None and selling_price > mrp:
            self.add_error("selling_price", "Selling price cannot be higher than MRP.")
        if self.instance.pk and cleaned.get("available_quantity", 0) < self.instance.reserved_quantity:
            self.add_error("available_quantity", "Quantity cannot be lower than stock reserved for open orders.")
        expiry = cleaned.get("expiry_date")
        from django.utils import timezone
        if expiry and expiry < timezone.localdate():
            self.add_error("expiry_date", "Expired batches cannot be listed for sale.")
        return cleaned


class PrescriptionUploadForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ["file", "customer_note"]
        widgets = {"customer_note": forms.TextInput(attrs={"class": "form-control", "maxlength": 240})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].widget.attrs.update({"class": "form-control", "accept": ".jpg,.jpeg,.png,.pdf"})

    def clean_file(self):
        file = self.cleaned_data["file"]
        if file.size > 10 * 1024 * 1024:
            raise ValidationError("File is too large. Maximum allowed size is 10 MB.")
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        if ext not in {"jpg", "jpeg", "png", "pdf"}:
            raise ValidationError("Upload a JPG, PNG, or PDF file.")
        content_type = getattr(file, "content_type", "")
        allowed = {"image/jpeg", "image/png", "application/pdf", "application/x-pdf", "image/pjpeg"}
        if content_type and content_type not in allowed:
            raise ValidationError("The uploaded file type does not match an allowed document type.")
        # Don't rely only on a filename or the client-supplied MIME type. Check basic file signatures.
        file.seek(0)
        signature = file.read(16)
        file.seek(0)
        valid_signature = {
            "jpg": signature.startswith(b"\xff\xd8\xff"),
            "jpeg": signature.startswith(b"\xff\xd8\xff"),
            "png": signature.startswith(b"\x89PNG\r\n\x1a\n"),
            "pdf": signature.startswith(b"%PDF-"),
        }.get(ext, False)
        if not valid_signature:
            raise ValidationError("The file contents do not match the selected document format.")
        return file


class CartAddForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=50, initial=1, widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 50}))


class CheckoutForm(forms.Form):
    fulfilment = forms.ChoiceField(choices=MarketplaceOrder.Fulfilment.choices, widget=forms.RadioSelect)
    prescription = forms.ModelChoiceField(queryset=Prescription.objects.none(), required=False, empty_label="Choose a prescription (if required)", widget=forms.Select(attrs={"class": "form-select"}))
    delivery_address = forms.CharField(required=False, max_length=300, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "House / street, locality, PIN code"}))
    customer_note = forms.CharField(required=False, max_length=300, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional instructions"}))

    def __init__(self, *args, customer=None, pharmacy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer
        self.pharmacy = pharmacy
        if customer is not None:
            self.fields["prescription"].queryset = Prescription.objects.filter(owner=customer, status__in=[Prescription.Status.PENDING, Prescription.Status.APPROVED]).order_by("-created_at")
        if pharmacy:
            choices = []
            if pharmacy.offers_pickup:
                choices.append((MarketplaceOrder.Fulfilment.PICKUP, "Collect from pharmacy"))
            if pharmacy.offers_delivery:
                choices.append((MarketplaceOrder.Fulfilment.DELIVERY, "Home delivery"))
            self.fields["fulfilment"].choices = choices
            if len(choices) == 1:
                self.fields["fulfilment"].initial = choices[0][0]

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("fulfilment")
        if self.pharmacy and mode == MarketplaceOrder.Fulfilment.DELIVERY:
            if not self.pharmacy.offers_delivery:
                self.add_error("fulfilment", "This pharmacy does not offer delivery.")
            if not cleaned.get("delivery_address", "").strip():
                self.add_error("delivery_address", "Enter a delivery address for home delivery.")
        if self.pharmacy and mode == MarketplaceOrder.Fulfilment.PICKUP and not self.pharmacy.offers_pickup:
            self.add_error("fulfilment", "This pharmacy does not offer pickup.")
        return cleaned
