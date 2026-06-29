// Copyright (c) 2026, Smoke Console Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Smoke Test Case", {
	refresh(frm) {
		// Re-sync the catalog from the frappe_smoke engine. Placed on the form
		// (served via doctype meta) so it works without a built JS bundle.
		frm.add_custom_button(__("Sync Catalog from Engine"), () => {
			frappe.call({ method: "smoke_console.api.sync_catalog" }).then((r) => {
				frappe.show_alert({
					message: __("Synced {0} test case(s)", [r.message]),
					indicator: "green",
				});
				frm.reload_doc();
			});
		});
	},
});
