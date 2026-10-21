# MedMitra UI Refresh v2

This update applies a cohesive visual redesign across the existing Django templates using a shared stylesheet, `static/css/ui-refresh.css`, loaded after `static/css/app.css`. Existing URL routes, forms, template logic, pharmacy workflows, profile pages and light/dark theme switch are preserved.

## Design updates
- Updated visual system with softer surfaces, clearer type scale, more spacious cards, refined buttons and focus states.
- Shared redesign for navigation, homepage, search/listing cards, pharmacy comparison, forms, auth pages, profiles, tables and dashboards.
- Responsive refinements for mobile/tablet and reduced-motion support.
- Theme-aware CSS variables support both light and dark mode.

## Verify locally
```powershell
python manage.py check
python manage.py test profiles
python manage.py runserver
```
The profile test suite may reveal existing redirect-related failures if local HTTPS redirection is enabled; see `PROFILE_SETUP.md` and review `SECURE_SSL_REDIRECT` for development.

## Deploy
Commit the UI stylesheet and base template update, push to GitHub, and let Render deploy the commit. No new migration is required.
