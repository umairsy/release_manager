app_name = "release_manager"
app_title = "Release Manager"
app_publisher = "Release Manager Contributors"
app_description = "Release testing control plane for release_tests — run release tests against Frappe sites and gate releases."
app_email = "umair_sayyed@yahoo.com"
app_license = "MIT"

# After install: load the test-case catalog from the engine and build dashboards.
after_install = "release_manager.install.after_install"

# Serve the Vue single-page UI at /release (vue-router history mode catch-all).
website_route_rules = [
    {"from_route": "/release/<path:app_path>", "to_route": "release"},
]

# Old /release URL now points at the rebranded /release app.
website_redirects = [
    {"source": "/smoke", "target": "/release"},
    {"source": r"/smoke/(.*)", "target": r"/release/\1"},
]

add_to_apps_screen = [
    {
        "name": "release_manager",
        "title": "Releases",
        "logo": "/assets/release_manager/release-logo.svg",
        "route": "/release",
    }
]

# Scheduled dispatch: run enabled Test Plans whose frequency matches.
scheduler_events = {
    "hourly": ["release_manager.api.run_hourly"],
    "daily": ["release_manager.api.run_daily"],
    "weekly": ["release_manager.api.run_weekly"],
}
