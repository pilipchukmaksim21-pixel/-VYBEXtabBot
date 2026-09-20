# VYBEX — no-code buttons, nested content and admin announcements

## Admin / manager registration
- `ADMIN_USERNAME=fvmfm1`
- `MANAGER_USERNAME=manager_VYBEX`
- `BOT_TOKEN` remains your existing Railway secret; do not paste it into chat.
- Optional legacy `ADMIN_ID` / `MANAGER_CHAT_ID` are still supported.

Both admin and manager should open `@VYBEXtabBot` and press `/start` once.

## No-code button builder
Admin → `/admin` → `🧩 Конструктор кнопок`.

You can:
- create main buttons;
- open any button in `📋 Управление кнопками`;
- add nested buttons inside it;
- add unlimited levels of nested buttons;
- set or change text;
- attach/change a Telegram video;
- delete a button together with its nested children.

Users see the created main buttons in the bot's main menu. Opening a button shows its text/video and nested buttons.

## Daily admin-only announcements
Admin → `/admin` → `📣 Реклама`.

The admin can create an announcement with text and optional video, set a daily time in `HH:MM`, and enable/disable it. The schedule uses `Europe/Warsaw` time.

Announcements are sent to registered ordinary users; admin and manager are excluded.

## Persistence
The bot stores `buttons.json`, `broadcast.json`, `users.json`, and `catalog.json` locally. Railway's normal filesystem can be reset on some redeploys/restarts. For production, use a persistent volume or database.


ADMIN BUTTON: The ⚙️ Адмін button is shown only to Telegram user ID 829871240. The /admin command is also restricted to this exact ID.
