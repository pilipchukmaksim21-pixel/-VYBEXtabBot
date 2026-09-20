# VYBEX — auto-registration admin/manager

This version keeps the no-code catalog and automatically registers the admin and manager by Telegram username when they press `/start`.

## Railway Variables
- `BOT_TOKEN` — your existing bot token (do not paste it into chat)
- `ADMIN_USERNAME=fvmfm1`
- `MANAGER_USERNAME=manager_VYBEX`
- `ADMIN_ID` and `MANAGER_CHAT_ID` are optional legacy fallbacks.

## First launch
1. Deploy this version.
2. From the admin account `@fvmfm1`, open `@VYBEXtabBot` and send `/start`.
3. From the manager account `@manager_VYBEX`, open `@VYBEXtabBot` and send `/start`.
4. The manager does not need to enter a numeric chat ID.
5. The admin can open `/admin` and manage the catalog.

The bot stores registrations in `users.json`. Railway's normal filesystem can be reset on some redeploys/restarts, so for a production version use a persistent database/volume.
