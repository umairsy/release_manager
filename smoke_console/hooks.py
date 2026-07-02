app_name = "smoke_console"
app_title = "Release Manager"
app_publisher = "Release Manager Contributors"
app_description = "Release testing control plane for frappe_smoke — run smoke tests against Frappe sites and gate releases."
app_email = "umair_sayyed@yahoo.com"
app_license = "MIT"

# After install: load the test-case catalog from the engine and build dashboards.
after_install = "smoke_console.install.after_install"

# Serve the Vue single-page UI at /release (vue-router history mode catch-all).
website_route_rules = [
    {"from_route": "/release/<path:app_path>", "to_route": "release"},
]

# Old /smoke URL now points at the rebranded /release app.
website_redirects = [
    {"source": "/smoke", "target": "/release"},
    {"source": r"/smoke/(.*)", "target": r"/release/\1"},
]

add_to_apps_screen = [
    {
        "name": "smoke_console",
        "title": "Releases",
        "route": "/release",
    }
]

# Scheduled dispatch: run enabled Test Plans whose frequency matches.
scheduler_events = {
    "hourly": ["smoke_console.api.run_hourly"],
    "daily": ["smoke_console.api.run_daily"],
    "weekly": ["smoke_console.api.run_weekly"],
}
