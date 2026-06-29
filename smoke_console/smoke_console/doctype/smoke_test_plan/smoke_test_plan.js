// Copyright (c) 2026, Smoke Console Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Smoke Test Plan", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Run Plan Now"), () => {
			frappe.call({ method: "smoke_console.api.run_plan", args: { plan: frm.doc.name } }).then((r) => {
				const runs = r.message || [];
				frappe.msgprint({
					title: __("Queued {0} run(s)", [runs.length]),
					message: runs.map((n) => `<a href="/app/smoke-run/${n}">${n}</a>`).join("<br>"),
					indicator: "blue",
				});
			});
		}).addClass("btn-primary");
	},
});
