// Copyright (c) 2026, Release Manager Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release Test Case", {
	refresh(frm) {
		// Re-sync the catalog from the release_tests engine. Placed on the form
		// (served via doctype meta) so it works without a built JS bundle.
		frm.add_custom_button(__("Sync Catalog from Engine"), () => {
			frappe.call({ method: "release_manager.api.sync_catalog" }).then((r) => {
				frappe.show_alert({
					message: __("Synced {0} test case(s)", [r.message]),
					indicator: "green",
				});
				frm.reload_doc();
			});
		});
	},
});
