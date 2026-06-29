// Copyright (c) 2026, Smoke Console Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Smoke Site", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Test Connection"), () => {
			frappe.dom.freeze(__("Connecting…"));
			frappe
				.call({ method: "smoke_console.api.test_connection", args: { site: frm.doc.name } })
				.then((r) => {
					frappe.dom.unfreeze();
					const res = r.message || {};
					if (res.ok) {
						frappe.show_alert({ message: res.status, indicator: "green" });
					} else {
						frappe.msgprint({
							title: __("Connection failed"),
							message: res.error,
							indicator: "red",
						});
					}
					frm.reload_doc();
				})
				.catch(() => frappe.dom.unfreeze());
		});
	},
});
