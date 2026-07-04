// Copyright (c) 2026, Release Manager Contributors and contributors
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
							method: "release_manager.api.run_group",
							args: { site, group: frm.doc.name },
						})
						.then((r) => {
							const run = r.message;
							frappe.msgprint({
								title: __("Run queued"),
								message: `<a href="/app/release-run/${run}">${run}</a>`,
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
