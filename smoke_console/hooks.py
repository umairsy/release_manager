app_name = "smoke_console"
app_title = "Smoke Console"
app_publisher = "Smoke Console Contributors"
app_description = "Control plane (UI) for frappe_smoke — run smoke tests against Frappe sites and track results."
app_email = "umair_sayyed@yahoo.com"
app_license = "MIT"

# After install: load the test-case catalog from the engine and build dashboards.
after_install = "smoke_console.install.after_install"

# Serve the Vue single-page UI at /smoke (vue-router history mode catch-all).
website_route_rules = [
    {"from_route": "/smoke/<path:app_path>", "to_route": "smoke"},
]

add_to_apps_screen = [
    {
        "name": "smoke_console",
        "title": "Smoke Console",
        "route": "/smoke",
    }
]

# Scheduled dispatch: run enabled Test Plans whose frequency matches.
scheduler_events = {
    "hourly": ["smoke_console.api.run_hourly"],
    "daily": ["smoke_console.api.run_daily"],
    "weekly": ["smoke_console.api.run_weekly"],
}
