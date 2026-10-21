# Homepage content: superuser admin guide

All newly added homepage CMS content is managed in Django Admin and is available only to a Django **superuser**. Pharmacy owners and ordinary staff accounts cannot add, edit, publish, or remove these records.

## Setup

1. Install the dependencies and copy `.env.example` to `.env` for local development.
2. Run `python manage.py migrate` so migration `marketplace.0002_homepage_content` creates the homepage content tables.
3. Run `python manage.py createsuperuser` if you do not already have a superuser.
4. Run `python manage.py runserver`, then sign in at `http://127.0.0.1:8000/admin/`.
5. Find these sections in the Marketplace group in Admin.

## What to manage

- **Homepage promotions / advertisements**: upload a banner image, write a title and optional subtitle, give it accessible alt text, optionally set an internal path such as `/medicines/` or an HTTPS destination, choose the display order, and optionally schedule start/end times. Set `is_active` off to hide it.
- **Homepage trust metrics**: add supportable figures or benefits such as verified listings, price transparency, and participating pharmacies. Use real numbers only when you can substantiate them.
- **Homepage customer reviews**: add genuine customer feedback only if you have permission to publish it. New reviews default to unpublished. Set `is_published` only after checking the review.
- **Homepage popular search terms**: choose one of four groups: healthcare products, medicines, frequently searched medicines, or vaccines. Leave the target URL blank to link to MedMitra search results; set a target URL only when you want a custom destination.
- **Homepage information / SEO sections**: add one or more informational sections about your actual services. Use plain text; line breaks are preserved. The first active item with a non-empty SEO description is used as the homepage description tag.

The public homepage shows only active promotions, active metrics, published reviews, active search terms, and active information sections. The new sections are intentionally empty until the superuser adds content; this avoids inventing customer reviews, advertising claims, search statistics, or business metrics.

## Uploaded banner files in production

Banner images upload into `MEDIA_ROOT/homepage/promotions/`. Local serving is configured for `DEBUG=True`. Before using uploaded images on a production host such as Render, configure durable private/public media storage (for example, an attached persistent disk or object storage). The default ephemeral application filesystem may be cleared during deploys or restarts. Never use the homepage banner feature to publish private prescription files or sensitive customer documents.

## Local command sequence

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver
```

## Footer social media links

Superusers can manage external profile links under **Marketplace → Footer social media links**. Choose a platform, enter its public HTTP(S) profile URL, optionally customize the label, set its order, and toggle it active. Only active links appear in the global footer. The section stays hidden if there are no active links. Non-superuser staff cannot manage these links. See `FOOTER_SOCIAL_LINKS_GUIDE.md` for the step-by-step procedure.

