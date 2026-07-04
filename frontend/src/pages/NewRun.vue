<template>
  <div class="p-6 max-w-3xl mx-auto space-y-6">
    <div class="flex items-center gap-2">
      <button class="text-ink-gray-5 hover:text-ink-gray-8" @click="router.back()">←</button>
      <h1 class="text-xl font-semibold">New Release Test</h1>
    </div>

    <div class="space-y-4 max-w-lg">
      <FormControl type="select" label="Test type" :options="typeOptions" v-model="testType" />

      <FormControl type="select" label="Site" :options="siteOptions" v-model="site" />
      <p v-if="selectedSite" class="text-sm text-ink-gray-5">
        Frappe version: <b>{{ selectedSite.frappe_version || "v16" }}</b>
        <span v-if="testType === 'UI'"> — runs the <code>cypress/e2e/{{ selectedSite.frappe_version || "v16" }}</code> specs.</span>
      </p>

      <template v-if="testType === 'API'">
        <FormControl
          type="select"
          label="Test Group (optional)"
          :options="groupOptions"
          v-model="group"
        />
        <p class="text-sm text-ink-gray-5">
          Pick a group to run all its test cases (e.g. “ERPNext - Distribution”), or leave it blank
          to run everything applicable on the site.
        </p>
      </template>

      <div v-else class="space-y-1">
        <FormControl
          type="checkbox"
          label="Show the browser while running (headed)"
          v-model="headed"
        />
        <p class="text-xs text-ink-gray-5">
          On by default: the browser window opens so you can watch the test run. Uncheck to run
          in the background (video only). Either way, on macOS the bench must be started from a
          Terminal (GUI) session for Cypress to launch.
        </p>
      </div>

      <ErrorMessage :message="create.error || uiCreate.error" />
      <div class="pt-2">
        <Button
          variant="solid"
          :loading="create.loading || uiCreate.loading"
          :disabled="!site"
          @click="run"
        >
          {{ testType === "UI" ? "Run UI test" : "Run" }}
        </Button>
      </div>
    </div>

    <!-- Running jobs terminal — only while something is actually running -->
    <div v-if="running.data && running.data.length">
      <div class="text-xs font-medium text-ink-gray-5 uppercase mb-1">Running jobs</div>
      <div class="rounded-lg bg-gray-900 text-gray-100 font-mono text-xs p-3 max-h-72 overflow-auto">
        <div v-for="r in running.data" :key="r.name" class="mb-2">
          <a class="text-blue-300 hover:underline" @click="router.push(`/runs/${r.name}`)">
            ▶ {{ r.run_title || r.name }} — {{ r.status }} ({{ r.site }})
          </a>
          <pre class="whitespace-pre-wrap text-gray-300">{{ r.log || "…" }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref } from "vue";
import { createListResource, createResource, ErrorMessage } from "frappe-ui";
import { useRouter } from "vue-router";

const router = useRouter();
const site = ref("");
const group = ref("");
const testType = ref("API");
const headed = ref(true);
const typeOptions = ["API", "UI"];

const sites = createListResource({
  doctype: "Testing Site",
  fields: ["name", "frappe_version"],
  filters: { enabled: 1 },
  pageLength: 100,
  auto: true,
});
const groups = createListResource({
  doctype: "Test Case Group",
  fields: ["name"],
  filters: { enabled: 1 },
  pageLength: 100,
  auto: true,
});
const running = createListResource({
  doctype: "Release Test",
  fields: ["name", "run_title", "site", "status", "log"],
  filters: { status: ["in", ["Queued", "Running"]] },
  orderBy: "modified desc",
  pageLength: 5,
  auto: true,
});

const siteOptions = computed(() => (sites.data || []).map((s) => s.name));
const groupOptions = computed(() => ["", ...(groups.data || []).map((g) => g.name)]);
const selectedSite = computed(() => (sites.data || []).find((s) => s.name === site.value));

const create = createResource({
  url: "release_manager.api.create_and_run",
  onSuccess: (name) => router.push(`/runs/${name}`),
});
const uiCreate = createResource({
  url: "release_manager.api.run_ui_test",
  onSuccess: (name) => router.push(`/runs/${name}`),
});

function run() {
  if (!site.value) return;
  if (testType.value === "UI") {
    uiCreate.submit({ site: site.value, headed: headed.value ? 1 : 0 });
  } else {
    create.submit({ site: site.value, group: group.value || null });
  }
}

// Keep the terminal live while jobs are in flight.
const timer = setInterval(() => running.reload(), 3000);
onUnmounted(() => clearInterval(timer));
</script>
