from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StaffProfile


class RegistrationPageTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)


class PharmacyRoleDashboardTests(TestCase):
    def test_pharmacist_goes_to_inventory(self):
        user = User.objects.create_user(username="pharmacy_demo", password="Safe-pass-12345")
        StaffProfile.objects.create(user=user, role=StaffProfile.Role.PHARMACIST, is_approved=True)
        self.client.force_login(user)
        response = self.client.get(reverse("staff_dashboard"))
        self.assertRedirects(response, reverse("pharmacy_dashboard"))

    def test_unapproved_pharmacy_staff_sees_pending_page(self):
        user = User.objects.create_user(username="pending_pharmacy", password="Safe-pass-12345")
        StaffProfile.objects.create(user=user, role=StaffProfile.Role.STORE_MANAGER, is_approved=False)
        self.client.force_login(user)
        response = self.client.get(reverse("staff_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pharmacy access pending")

    def test_customer_cannot_open_staff_dashboard(self):
        user = User.objects.create_user(username="regular_demo", password="Safe-pass-12345")
        self.client.force_login(user)
        response = self.client.get(reverse("staff_dashboard"))
        self.assertRedirects(response, reverse("profile_overview"))
