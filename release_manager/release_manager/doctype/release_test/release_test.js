// Copyright (c) 2026, Release Manager Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Release Test", {
	refresh(frm) {
		if (frm.is_new()) return;

		const running = ["Queued", "Running"].includes(frm.doc.status);
		if (!running) {
			frm.add_custom_button(__("Run Now"), () => {
				frappe.call({ method: "release_manager.api.run_now", args: { run: frm.doc.name } }).then(() => {
					frappe.show_alert({ message: __("Run queued"), indicator: "blue" });
					frm.reload_doc();
				});
			}).addClass("btn-primary");
		} else {
			// Auto-refresh while the background job is in flight.
			frm.dashboard.set_headline(__("Run is {0}…", [frm.doc.status]));
			setTimeout(() => frm.reload_doc(), 3000);
		}

		const colors = { Passed: "green", Partial: "orange", Failed: "red", Running: "blue", Queued: "blue" };
		if (frm.doc.status && colors[frm.doc.status]) {
			frm.page.set_indicator(frm.doc.status, colors[frm.doc.status]);
		}
	},
});
