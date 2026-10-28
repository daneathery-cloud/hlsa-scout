# HLSA Scout - Changelog

Version numbers: MAJOR.MINOR.PATCH. The version shows in the window title, the top-right of every page and the README.
Bump `APP_VERSION` / `APP_VERSION_DATE` in `config.py` (and the README line) for every change.

## 1.2.0 - 2026-10-27
- Hand-off to HLSA Pipeline (the CRM): the phone edition now also publishes `leads.json` (the same public
  NPI registry and news data already shown on its pages), which the CRM's Scout Leads tab reads.
- Desktop Watchlist: new "Send to HLSA Pipeline" button downloads your saved items (with status and notes)
  as a file the CRM can load.

## 1.1.0 - 2026-10-25
- Phone edition: https://daneathery-cloud.github.io/hlsa-scout/ - the same pages, built from a scan GitHub runs twice a
  day (about 7:15 am / 4:15 pm Central) and after every code change. Per-phone watchlist with status/notes, share,
  free versions (looked up in advance), report/CSV export, add-to-home-screen app icon, "newer scan" banner, Diagnostics.
- Organizations on the phone are NEW for 7 days after they first appear.
- Laptop app: "Phone version" link in the header; README section about the phone edition.
- Layout: pages now fit phone screens (organization table becomes cards, filter rows scroll sideways).

## 1.0.0 - 2026-10-25
First release.
- Town-by-town Google News search across Bexar County, the counties touching Bexar, the I-35 Corridor to Austin and the
  Hill Country / rural ring, plus direct local and trade-press feeds.
- Seven opportunity categories; "Could help" partner tags (NT Partnership first) for HLSA's Trusted Referral Partners.
- New Organizations: healthcare organizations registered in the last 90 days from the free CMS NPI Registry, with
  "NEW since last scan" badges.
- Watchlist with lead status + notes, share buttons, watchlist report (HTML) and Excel (CSV) export.
- 🔓 Free versions button on subscription-site stories.
- Data kept in %LOCALAPPDATA%\HLSAScout; log + Copy Diagnostics.
