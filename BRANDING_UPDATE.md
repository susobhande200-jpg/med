# MedMitra branding update

The public-facing pharmacy website brand is **MedMitra**.

## Changed

- Updated the shared navbar and footer wordmark, accessibility labels, homepage headings, metadata, content pages, registration/profile text, email subjects, and Django Admin headings.
- Updated the default email sender name and account-export filename.
- Updated homepage search-term help text with a small database-state migration (`marketplace.0004_homepage_search_term_brand_help_text`).
- Updated tests that check the displayed brand and social-link rendering.
- Renamed the extracted project folder in this ZIP to `MedMitra`.

## Compatibility preserved

- Django Python package names, app labels, named routes, database tables and relationships remain unchanged.
- Existing email-verification signing salts and local theme-storage keys remain unchanged so outstanding verification links and saved display preferences are not invalidated.
- The previous Render hostname and resource slugs remain unchanged in deployment configuration. The visible brand becomes MedMitra, but changing the deployed URL/service name is a separate hosting task.

## Apply and verify

From the folder containing `manage.py`, run:

```powershell
python manage.py migrate
python manage.py check
python manage.py test
```

Django's runtime checks could not be run during packaging because the packaging environment does not have Django installed and network access prevented installing it. Run the commands above in the project's configured Python environment before deployment.
