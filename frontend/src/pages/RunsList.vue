<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-semibold">Smoke Runs</h1>
      <Button variant="solid" @click="router.push('/new')">New Run</Button>
    </div>

    <div class="border rounded-lg divide-y">
      <div
        v-for="r in runs.data"
        :key="r.name"
        class="flex items-center gap-3 p-3 hover:bg-surface-gray-1 cursor-pointer"
        @click="router.push(`/runs/${r.name}`)"
      >
        <Badge :theme="theme(r.status)" :label="r.status" />
        <div class="flex-1 min-w-0">
          <div class="font-medium truncate">{{ r.run_title || r.name }}</div>
          <div class="text-sm text-ink-gray-5">{{ r.site }} · {{ r.name }}</div>
        </div>
        <div class="text-sm whitespace-nowrap">
          <span class="text-ink-green-3">{{ r.passed }} pass</span>
          <span v-if="r.failed" class="text-ink-red-3 ml-2">{{ r.failed }} fail</span>
          <span v-if="r.skipped" class="text-ink-gray-4 ml-2">{{ r.skipped }} skip</span>
        </div>
      </div>
      <div v-if="runs.data && !runs.data.length" class="p-8 text-center text-ink-gray-5">
        No runs yet. Start one with “New Run”.
      </div>
    </div>
  </div>
</template>

<script setup>
import { createListResource } from "frappe-ui";
import { useRouter } from "vue-router";
import { statusTheme } from "@/lib/status";

const router = useRouter();
const theme = statusTheme;

const runs = createListResource({
  doctype: "Smoke Run",
  fields: ["name", "run_title", "site", "status", "passed", "failed", "skipped", "modified"],
  orderBy: "modified desc",
  pageLength: 50,
  auto: true,
});
</script>
