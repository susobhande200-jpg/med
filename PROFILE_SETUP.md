# MedMitra Profile Management

The `profiles` Django app is registered in `config/settings.py` and routed at `/profile/` through `config/urls.py`. The authenticated navbar in `templates/base.html` contains a **My profile** link for desktop and mobile navigation.

## Local setup (Windows)

Run from the directory containing `manage.py`:

```powershell
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py test profiles
python manage.py runserver
```

Sign in, then open http://127.0.0.1:8000/profile/.

## Commit and deploy

Review changes and confirm `.env`, private prescription files, local databases, and credentials are not staged:

```powershell
git status
git add profiles templates/profiles static/profiles config/settings.py config/urls.py templates/base.html PROFILE_SETUP.md
git status
git commit -m "Integrate MedMitra profile management"
git push origin main
```

If Render is connected to this GitHub branch with automatic deploy enabled, it should deploy the new commit. Otherwise trigger **Manual Deploy → Deploy latest commit**.

## Notes

- Do not include `.env`, `db.sqlite3`, private prescription uploads, or `.git` in a source ZIP shared publicly.
- The profile app uses Django's existing authentication and existing pharmacy/catalogue models. Run the Django tests locally before treating the feature as production-ready.
- This ZIP is a source distribution, not a backup of your production database or uploaded customer documents.
