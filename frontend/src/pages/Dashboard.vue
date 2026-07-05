<template>
  <div class="p-6 max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-ink-gray-9">Release Manager</h1>
        <p class="text-sm text-ink-gray-5">Run release tests against your Frappe sites and track results.</p>
      </div>
      <Button variant="solid" @click="router.push('/new')">New Release Test</Button>
    </div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
      <div v-for="c in cards" :key="c.label" class="rounded-lg border bg-white p-4 flex items-start gap-3">
        <div class="rounded-md p-2" :class="c.iconBg">
          <FeatherIcon :name="c.icon" class="h-4 w-4" :class="c.iconColor" />
        </div>
        <div class="min-w-0">
          <div class="text-2xl font-semibold text-ink-gray-9 leading-tight">{{ c.value ?? "–" }}</div>
          <div class="text-xs text-ink-gray-5">{{ c.label }}</div>
        </div>
      </div>
    </div>

    <!-- Recent runs -->
    <div class="rounded-lg border bg-white">
      <div class="flex items-center justify-between px-4 py-3 border-b">
        <div class="font-medium text-ink-gray-8">Recent runs</div>
        <Button variant="ghost" @click="router.push('/new')">New</Button>
      </div>
      <div class="divide-y">
        <div
          v-for="r in runs.data"
          :key="r.name"
          class="flex items-center gap-3 px-4 py-3 hover:bg-surface-gray-1 cursor-pointer"
          @click="router.push(`/runs/${r.name}`)"
        >
          <Badge :theme="statusTheme(r.status)" :label="r.status" />
          <Badge v-if="r.layer === 'UI'" theme="blue" label="UI" />
          <div class="flex-1 min-w-0">
            <div class="font-medium text-ink-gray-8 truncate">{{ r.run_title || r.name }}</div>
            <div class="text-xs text-ink-gray-5 truncate">{{ r.site }} · {{ r.name }}</div>
          </div>
          <div class="text-sm whitespace-nowrap">
            <span class="text-ink-green-3 font-medium">{{ r.passed }}</span>
            <span v-if="r.failed" class="text-ink-red-3 font-medium ml-1">/ {{ r.failed }}</span>
          </div>
          <div class="text-xs text-ink-gray-4 w-24 text-right hidden sm:block">{{ timeAgo(r.modified) }}</div>
        </div>
        <div v-if="runs.data && !runs.data.length" class="p-10 text-center text-ink-gray-5">
          No runs yet — start one from “New Release Test”.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted } from "vue";
import { Badge, Button, FeatherIcon, createListResource, createResource } from "frappe-ui";
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

const cards = computed(() => {
  const s = stats.data || {};
  return [
    { label: "Runs", value: s.runs, icon: "play", iconBg: "bg-surface-gray-2", iconColor: "text-ink-gray-6" },
    { label: "API tests", value: s.api_tests, icon: "server", iconBg: "bg-surface-gray-2", iconColor: "text-ink-gray-6" },
    { label: "UI tests", value: s.ui_tests, icon: "monitor", iconBg: "bg-blue-50", iconColor: "text-blue-600" },
    { label: "Transactions", value: s.transactions, icon: "repeat", iconBg: "bg-surface-gray-2", iconColor: "text-ink-gray-6" },
    { label: "Passed", value: s.passed, icon: "check-circle", iconBg: "bg-green-50", iconColor: "text-green-600" },
    { label: "Failed", value: s.failed, icon: "x-circle", iconBg: "bg-red-50", iconColor: "text-red-600" },
  ];
});

// Poll so counters + recent runs stay live while jobs run.
const timer = setInterval(() => {
  stats.reload();
  runs.reload();
}, 3000);
onUnmounted(() => clearInterval(timer));

function timeAgo(dt) {
  if (!dt) return "";
  const then = new Date(dt.replace(" ", "T"));
  const secs = Math.max(0, (Date.now() - then.getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = secs / 60;
  if (mins < 60) return `${Math.floor(mins)}m ago`;
  const hrs = mins / 60;
  if (hrs < 24) return `${Math.floor(hrs)}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
</script>
