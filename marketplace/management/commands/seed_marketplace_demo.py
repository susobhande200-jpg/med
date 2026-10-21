import secrets
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from marketplace.models import MedicineCategory, MedicineProduct, Pharmacy, PharmacyListing


class Command(BaseCommand):
    help = "Create clearly fictional MedMitra sample catalogue data. Use --create-demo-users to add local-only sample stores."

    def add_arguments(self, parser):
        parser.add_argument("--create-demo-users", action="store_true", help="Create local demo store owners and verified sample pharmacies with generated passwords.")

    def handle(self, *args, **options):
        categories_data = [
            ("Everyday essentials", "everyday-essentials", "bi-bandaid"),
            ("Vitamins & wellness", "vitamins-wellness", "bi-heart-pulse"),
            ("First aid", "first-aid", "bi-bandaid-fill"),
            ("Health devices", "health-devices", "bi-thermometer-half"),
        ]
        categories = {}
        for name, slug, icon in categories_data:
            obj, _ = MedicineCategory.objects.update_or_create(slug=slug, defaults={"name": name, "icon": icon, "active": True})
            categories[slug] = obj

        products_data = [
            {"brand_name": "DEMO Paracetamol 500 mg", "generic_name": "Sample active ingredient", "strength": "500 mg", "dosage_form": "tablet", "pack_size": "10 tablets (demo pack)", "manufacturer": "Fictional Demo Manufacturer", "category": categories["everyday-essentials"], "description": "Fictional catalogue item for software testing only. Not a real product or medical recommendation.", "requires_prescription": False},
            {"brand_name": "DEMO ORS Sachet", "generic_name": "Sample oral rehydration salts", "strength": "Standard demo pack", "dosage_form": "other", "pack_size": "1 sachet (demo pack)", "manufacturer": "Fictional Demo Manufacturer", "category": categories["everyday-essentials"], "description": "Fictional catalogue item for software testing only.", "requires_prescription": False},
            {"brand_name": "DEMO Vitamin C", "generic_name": "Sample vitamin supplement", "strength": "500 mg", "dosage_form": "tablet", "pack_size": "10 tablets (demo pack)", "manufacturer": "Fictional Demo Manufacturer", "category": categories["vitamins-wellness"], "description": "Fictional catalogue item for software testing only. Not a real product or supplement recommendation.", "requires_prescription": False},
            {"brand_name": "DEMO First Aid Cream", "generic_name": "Sample topical product", "strength": "Demo formula", "dosage_form": "cream", "pack_size": "15 g demo tube", "manufacturer": "Fictional Demo Manufacturer", "category": categories["first-aid"], "description": "Fictional catalogue item for software testing only.", "requires_prescription": False},
            {"brand_name": "DEMO Digital Thermometer", "generic_name": "Temperature measuring device", "strength": "N/A", "dosage_form": "device", "pack_size": "1 demo device", "manufacturer": "Fictional Demo Manufacturer", "category": categories["health-devices"], "description": "Fictional medical-device catalogue entry for software testing only.", "requires_prescription": False},
        ]
        products = []
        for row in products_data:
            product, _ = MedicineProduct.objects.update_or_create(brand_name=row["brand_name"], strength=row["strength"], defaults={**row, "active": True})
            products.append(product)

        if not options["create_demo_users"]:
            self.stdout.write(self.style.SUCCESS(f"Added {len(categories)} demo categories and {len(products)} fictional catalogue items."))
            self.stdout.write("No demo pharmacy users were created. Run with --create-demo-users for local marketplace listings.")
            return

        User = get_user_model()
        owners = []
        for username, full_name in [("demo_greenleaf_owner", "Demo GreenLeaf Owner"), ("demo_carepoint_owner", "Demo CarePoint Owner")]:
            user, created = User.objects.get_or_create(username=username, defaults={"first_name": full_name.split()[1], "last_name": full_name.split()[2]})
            if created:
                password = secrets.token_urlsafe(14)
                user.set_password(password)
                user.save(update_fields=["password"])
                owners.append((username, password))
            owners.append((username, "(existing account; password not changed)")) if not created else None

        pharmacy_data = [
            {"owner": User.objects.get(username="demo_greenleaf_owner"), "name": "DEMO GreenLeaf Pharmacy", "phone": "0000000001", "email": "greenleaf-demo@example.invalid", "address": "123 Sample Road", "locality": "Demo Market", "city": "Sampletown", "state": "West Bengal", "pincode": "000000", "licence_number": "DEMO-LICENCE-001", "pharmacist_name": "Demo Pharmacist A", "pharmacist_registration": "DEMO-REG-001", "offers_delivery": True, "offers_pickup": True, "delivery_fee": Decimal("25.00"), "verification_status": Pharmacy.VerificationStatus.APPROVED},
            {"owner": User.objects.get(username="demo_carepoint_owner"), "name": "DEMO CarePoint Chemist", "phone": "0000000002", "email": "carepoint-demo@example.invalid", "address": "45 Example Avenue", "locality": "Demo Crossing", "city": "Sampletown", "state": "West Bengal", "pincode": "000000", "licence_number": "DEMO-LICENCE-002", "pharmacist_name": "Demo Pharmacist B", "pharmacist_registration": "DEMO-REG-002", "offers_delivery": False, "offers_pickup": True, "delivery_fee": Decimal("0.00"), "verification_status": Pharmacy.VerificationStatus.APPROVED},
        ]
        pharmacies = []
        for row in pharmacy_data:
            owner = row.pop("owner")
            pharmacy, _ = Pharmacy.objects.update_or_create(name=row["name"], defaults={**row, "owner": owner})
            pharmacies.append(pharmacy)

        prices = [
            [(Decimal("35.00"), Decimal("24.00"), 22), (Decimal("30.00"), Decimal("23.00"), 9)],
            [(Decimal("22.00"), Decimal("18.00"), 50), (Decimal("21.00"), Decimal("19.00"), 7)],
            [(Decimal("80.00"), Decimal("68.00"), 14), (Decimal("76.00"), Decimal("70.00"), 11)],
            [(Decimal("95.00"), Decimal("81.00"), 6), (Decimal("90.00"), Decimal("82.00"), 3)],
            [(Decimal("150.00"), Decimal("119.00"), 12), (Decimal("140.00"), Decimal("125.00"), 4)],
        ]
        listing_count = 0
        for product, store_prices in zip(products, prices):
            for pharmacy, price in zip(pharmacies, store_prices):
                mrp, sell, quantity = price
                PharmacyListing.objects.update_or_create(pharmacy=pharmacy, product=product, defaults={"mrp": mrp, "selling_price": sell, "available_quantity": quantity, "reserved_quantity": 0, "batch_number": "DEMO-BATCH", "expiry_date": None, "active": True})
                listing_count += 1
        self.stdout.write(self.style.SUCCESS(f"Added {len(categories)} categories, {len(products)} fictional catalogue items, {len(pharmacies)} demo pharmacies and {listing_count} listings."))
        self.stdout.write(self.style.WARNING("Demo listings are fictional and must never be used for real medicine sales or medical decisions."))
        for username, password in owners:
            if password.startswith("("):
                self.stdout.write(f"{username}: {password}")
            else:
                self.stdout.write(f"Demo owner login — username: {username} | temporary password: {password}")
