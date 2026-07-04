<template>
  <div class="p-6 max-w-6xl mx-auto space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-semibold">Release Manager</h1>
      <div class="flex gap-2">
        <Button variant="solid" @click="router.push('/new')">New Release Test</Button>
        <Button variant="subtle" :disabled="true" title="Coming soon">Release (coming soon)</Button>
      </div>
    </div>

    <!-- Counter cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <Stat label="Runs" :value="stats.data?.runs" />
      <Stat label="API tests" :value="stats.data?.api_tests" />
      <Stat label="UI tests" :value="stats.data?.ui_tests" tone="blue" />
      <Stat label="Transactions" :value="stats.data?.transactions" />
      <Stat label="Passed" :value="stats.data?.passed" tone="green" />
      <Stat label="Failed" :value="stats.data?.failed" tone="red" />
      <Stat label="Skipped" :value="stats.data?.skipped" tone="gray" />
    </div>

    <!-- Recent runs -->
    <div>
      <div class="text-xs font-medium text-ink-gray-5 uppercase mb-1">Recent runs</div>
      <div class="border rounded-lg divide-y">
        <div
          v-for="r in runs.data"
          :key="r.name"
          class="flex items-center gap-3 p-3 hover:bg-surface-gray-1 cursor-pointer"
          @click="router.push(`/runs/${r.name}`)"
        >
          <Badge :theme="statusTheme(r.status)" :label="r.status" />
          <Badge v-if="r.layer === 'UI'" theme="blue" label="UI" />
          <div class="flex-1 min-w-0">
            <div class="font-medium truncate">{{ r.run_title || r.name }}</div>
            <div class="text-sm text-ink-gray-5">{{ r.site }} · {{ r.name }}</div>
          </div>
          <div class="text-sm whitespace-nowrap">
            <span class="text-ink-green-3">{{ r.passed }} pass</span>
            <span v-if="r.failed" class="text-ink-red-3 ml-2">{{ r.failed }} fail</span>
          </div>
        </div>
        <div v-if="runs.data && !runs.data.length" class="p-8 text-center text-ink-gray-5">
          No runs yet.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { h, onUnmounted } from "vue";
import { Badge, Button, createListResource, createResource } from "frappe-ui";
import { useRouter } from "vue-router";
import { statusTheme } from "@/lib/status";

const router = useRouter();

const stats = createResource({ url: "release_manager.api.dashboard_stats", auto: true });
const runs = createListResource({
  doctype: "Release Test",
  fields: ["name", "run_title", "site", "status", "layer", "passed", "failed", "modified"],
  orderBy: "modified desc",
  pageLength: 15,
  auto: true,
});

// Poll so counters + recent runs stay live while jobs run.
const timer = setInterval(() => {
  stats.reload();
  runs.reload();
}, 3000);
onUnmounted(() => clearInterval(timer));

// Tiny inline stat-card component.
const Stat = (props) =>
  h("div", { class: "border rounded-lg p-3" }, [
    h("div", { class: "text-2xl font-semibold " + toneClass(props.tone) }, String(props.value ?? "–")),
    h("div", { class: "text-xs text-ink-gray-5" }, props.label),
  ]);
Stat.props = ["label", "value", "tone"];
function toneClass(tone) {
  return { green: "text-ink-green-3", red: "text-ink-red-3", gray: "text-ink-gray-5", blue: "text-ink-blue-3" }[tone] || "";
}
</script>
