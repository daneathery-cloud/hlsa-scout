# HLSA Scout - Changelog

Version numbers: MAJOR.MINOR.PATCH. The version shows in the window title, the top-right of every page and the README.
Bump `APP_VERSION` / `APP_VERSION_DATE` in `config.py` (and the README line) for every change.

## 1.3.1 - 2026-10-31
- Business plan section 2: principals' bios, NT Partnership's pre-formation status, HLSA's leadership and organization,
  related-party and 501(c)(6)-vs-(c)(3) considerations; LLC formation steps in the roadmap; related-party risk.
- Principals' bios live in plan_private.py, which is git-ignored (the repository is public) and bundled only into the exe.

## 1.3.0 - 2026-10-31
- New laptop-only tab "Market & Plan": NT Partnership market analysis and business plan.
  - Market data (scanners/market.py, cached a week): CMS home health + hospice enrollments, owners and 2024 Medicare
    volume (market share by parent owner, HHI, chain vs owner-operated), nursing-home Payroll-Based Journal contract
    hours, Medicare-billing clinicians by specialty, BLS workforce and pay for the SA and Austin metros.
  - Uses HLSA Scout's own scan too: new NPI organizations (new-practice formation) and regional stories.
  - Ranked niche opportunities with evidence and named targets; researched competitor landscape (config.COMPETITORS).
  - 12-section business plan incl. the HLSA Consulting Collective and the HLSA relationship structure.
  - Editable 3-year financial model (saved per computer); "Download business plan" (Word-openable).
- Never published to the phone edition.

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
