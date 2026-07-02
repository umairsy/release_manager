// Copyright (c) 2026, Smoke Console Contributors and contributors
// For license information, please see license.txt

frappe.ui.form.on("Test Case Group", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Run Group"), () => {
			frappe.prompt(
				[
					{
						fieldname: "site",
						fieldtype: "Link",
						options: "Testing Site",
						label: __("Site"),
						reqd: 1,
					},
				],
				({ site }) => {
					frappe
						.call({
							method: "smoke_console.api.run_group",
							args: { site, group: frm.doc.name },
						})
						.then((r) => {
							const run = r.message;
							frappe.msgprint({
								title: __("Run queued"),
								message: `<a href="/app/smoke-run/${run}">${run}</a>`,
								indicator: "blue",
							});
						});
				},
				__("Run {0}", [frm.doc.name]),
				__("Run")
			);
		}).addClass("btn-primary");
	},
});
