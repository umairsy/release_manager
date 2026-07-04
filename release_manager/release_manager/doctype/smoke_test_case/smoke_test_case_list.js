// Copyright (c) 2026, Release Manager Contributors and contributors
// For license information, please see license.txt

frappe.listview_settings["Smoke Test Case"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Sync Catalog"), () => {
			frappe.call({ method: "release_manager.api.sync_catalog" }).then((r) => {
				frappe.show_alert({
					message: __("Synced {0} test case(s) from the engine", [r.message]),
					indicator: "green",
				});
				listview.refresh();
			});
		});
	},
};
