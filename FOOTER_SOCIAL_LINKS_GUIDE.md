# MedMitra footer social links

Social links are managed by a Django superuser. Pharmacy owners and regular staff cannot create or edit this homepage/footer content.

## Add or update a link

1. Run database migrations with `python manage.py migrate`.
2. Sign in at `/admin/` using a Django superuser account.
3. Open **Marketplace → Footer social media links**.
4. Add a platform, public HTTP(S) URL, optional display label, display order, and whether it should open in a new tab.
5. Leave **Active** checked to publish the link. Uncheck it to hide the link without deleting it.

Instagram, Facebook, YouTube, LinkedIn, X, WhatsApp, Telegram, and Other are supported. The icon is selected automatically from the platform. If all links are inactive or none have been added, the public footer section remains hidden.

Only use profile/page URLs that MedMitra owns or is authorised to link to. Do not enter credentials or private tokens in URL fields.
