from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketplace.models import MedicineProduct, Pharmacy
from .models import CustomerAddress, ProfilePreferences, SavedMedicine, SavedPharmacy

User = get_user_model()


class ProfileManagementTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="customer_one", password="TestPass!23456", email="customer@example.com")
        self.other = User.objects.create_user(username="customer_two", password="TestPass!23456", email="other@example.com")

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile_overview"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_customer_profile_overview_loads_and_creates_preferences(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile_overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your profile")
        self.assertTrue(ProfilePreferences.objects.filter(user=self.customer).exists())

    def test_user_cannot_edit_another_users_address(self):
        address = CustomerAddress.objects.create(
            user=self.other,
            recipient_name="Other User",
            phone="9876543210",
            address_line1="12 Example Road",
            city="Kolkata",
            state="West Bengal",
            pincode="700001",
        )
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile_address_edit", args=[address.pk]))
        self.assertEqual(response.status_code, 404)

    def test_address_is_saved_as_default_when_first_address(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse("profile_address_add"), {
            "recipient_name": "Test Customer",
            "phone": "9876543210",
            "address_line1": "14 Main Road",
            "locality": "Central",
            "city": "Kolkata",
            "state": "West Bengal",
            "pincode": "700001",
            "address_type": "home",
        })
        self.assertRedirects(response, reverse("profile_addresses"))
        address = CustomerAddress.objects.get(user=self.customer)
        self.assertTrue(address.is_default)

    def test_data_export_is_private_and_contains_only_own_account(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("attachment; filename=\"medmitra-account-export.json\"", response["Content-Disposition"])
        self.assertEqual(response.json()["account"]["username"], "customer_one")

    def test_preferences_save_does_not_clear_personal_contact_fields(self):
        prefs = ProfilePreferences.objects.create(user=self.customer, contact_phone="9876543210")
        self.client.force_login(self.customer)
        response = self.client.post(reverse("profile_preferences"), {
            "preferred_language": "bn",
            "preferred_fulfilment": "delivery",
            "notify_order_updates": "on",
            "notify_prescription_updates": "on",
            "notify_inventory_alerts": "on",
        })
        self.assertRedirects(response, reverse("profile_preferences"))
        prefs.refresh_from_db()
        self.assertEqual(prefs.contact_phone, "9876543210")
        self.assertEqual(prefs.preferred_language, "bn")
        self.assertEqual(prefs.preferred_fulfilment, "delivery")

    def test_customer_can_save_and_remove_a_medicine(self):
        product = MedicineProduct.objects.create(brand_name="Test medicine", active=True)
        self.client.force_login(self.customer)
        response = self.client.post(reverse("profile_save_medicine", args=[product.pk]), {"next": reverse("profile_saved_items")})
        self.assertRedirects(response, reverse("profile_saved_items"))
        self.assertTrue(SavedMedicine.objects.filter(user=self.customer, product=product).exists())
        self.client.post(reverse("profile_save_medicine", args=[product.pk]), {"next": reverse("profile_saved_items")})
        self.assertFalse(SavedMedicine.objects.filter(user=self.customer, product=product).exists())

    def test_customer_cannot_see_another_users_saved_items(self):
        product = MedicineProduct.objects.create(brand_name="Private medicine", active=True)
        SavedMedicine.objects.create(user=self.other, product=product)
        self.client.force_login(self.customer)
        response = self.client.get(reverse("profile_saved_items"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private medicine")

    def test_customer_can_save_a_verified_pharmacy(self):
        pharmacy = Pharmacy.objects.create(
            owner=self.other,
            name="Test Verified Pharmacy",
            phone="9876543210",
            address="1 Test Road",
            city="Kolkata",
            pincode="700001",
            verification_status=Pharmacy.VerificationStatus.APPROVED,
        )
        self.client.force_login(self.customer)
        response = self.client.post(reverse("profile_save_pharmacy", args=[pharmacy.pk]), {"next": reverse("profile_saved_items")})
        self.assertRedirects(response, reverse("profile_saved_items"))
        self.assertTrue(SavedPharmacy.objects.filter(user=self.customer, pharmacy=pharmacy).exists())
