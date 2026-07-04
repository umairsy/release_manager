<template>
  <div class="max-w-6xl mx-auto p-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-1">
      <button class="text-ink-gray-5 hover:text-ink-gray-8" @click="router.push('/')">←</button>
      <h1 class="text-xl font-semibold">{{ run.doc?.run_title || name }}</h1>
      <Badge :theme="statusTheme(run.doc?.status)" :label="run.doc?.status || '…'" />
      <div class="flex-1" />
      <Button :loading="rerunRes.loading" @click="rerunRes.submit({ run: name })">Run again</Button>
    </div>
    <div class="text-sm text-ink-gray-5 mb-4">
      {{ run.doc?.site }} ·
      <span v-if="run.doc?.total_steps">
        {{ run.doc?.passed }} pass / {{ run.doc?.failed }} fail / {{ run.doc?.skipped }} skip
      </span>
      <span v-if="run.doc?.started_at"> · started {{ run.doc.started_at }}</span>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Left: suites (tasks) -->
      <div class="border rounded-lg divide-y self-start">
        <div class="px-3 py-2 text-xs font-medium text-ink-gray-5 uppercase">Suites</div>
        <button
          v-for="r in results.data"
          :key="r.name"
          class="w-full text-left flex items-center gap-3 p-3 hover:bg-surface-gray-1"
          :class="selected === r.name ? 'bg-surface-gray-2' : ''"
          @click="select(r)"
        >
          <Badge :theme="statusTheme(r.status)" :label="r.status" />
          <span class="flex-1 font-medium">{{ r.suite }}</span>
          <span class="text-xs text-ink-gray-4">{{ r.duration_ms }} ms</span>
        </button>
        <div v-if="results.data && !results.data.length" class="p-4 text-sm text-ink-gray-5">
          {{ isRunning ? "Running…" : "No results." }}
        </div>
      </div>

      <!-- Output / log — always available; the only place errors show when a run
           produced no results (e.g. a UI run whose browser failed to launch). -->
      <div v-if="run.doc?.log" class="md:col-span-2 border rounded-lg self-start">
        <div class="px-3 py-2 text-xs font-medium text-ink-gray-5 uppercase">Output / log</div>
        <pre class="m-0 rounded-b-lg bg-gray-900 text-gray-100 font-mono text-xs p-3 max-h-96 overflow-auto whitespace-pre-wrap">{{ run.doc.log }}</pre>
      </div>

      <!-- Right: Output + Next actionable -->
      <div class="border rounded-lg self-start">
        <div v-if="!detail.data" class="p-6 text-sm text-ink-gray-5">
          Select a suite to see its steps and output.
        </div>
        <div v-else class="divide-y">
          <div class="px-3 py-2 text-xs font-medium text-ink-gray-5 uppercase">
            {{ detail.data.suite }} — steps
          </div>
          <div v-for="(s, i) in detail.data.steps" :key="i" class="p-3 text-sm">
            <div class="flex items-center gap-2">
              <Badge :theme="statusTheme(s.status)" :label="s.status" />
              <span class="flex-1">{{ s.step }}</span>
              <span class="text-xs text-ink-gray-4">{{ s.duration_ms }} ms</span>
            </div>
            <pre v-if="s.error" class="mt-1 text-xs text-ink-red-3 whitespace-pre-wrap">{{ s.error }}</pre>
          </div>

          <!-- Next actionable -->
          <div class="p-3 space-y-2 bg-surface-gray-1">
            <div class="text-xs font-medium text-ink-gray-5 uppercase">Next actionable</div>
            <FormControl
              type="select"
              label="Action status"
              :options="['Open', 'Investigating', 'Resolved', 'Not Required']"
              v-model="form.action_status"
            />
            <FormControl
              type="textarea"
              label="Corrective action"
              v-model="form.corrective_action"
            />
            <div class="flex gap-2">
              <Button variant="solid" :loading="saveRes.loading" @click="save">Save</Button>
              <Button :loading="rerunSuite.loading" @click="rerunOneSuite">Re-run this suite</Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, reactive, ref, watch } from "vue";
import { Badge, createDocumentResource, createListResource, createResource } from "frappe-ui";
import { useRouter } from "vue-router";
import { statusTheme, RUNNING_STATES } from "@/lib/status";

const props = defineProps({ name: String });
const router = useRouter();
const name = props.name;

const run = createDocumentResource({ doctype: "Release Test", name, auto: true });
const results = createListResource({
  doctype: "Test Result",
  fields: ["name", "suite", "status", "duration_ms", "action_status", "corrective_action"],
  filters: { run: name },
  orderBy: "suite asc",
  pageLength: 100,
  auto: true,
});

const selected = ref(null);
const detail = createResource({ url: "frappe.client.get" });
const form = reactive({ action_status: "Open", corrective_action: "" });

function select(r) {
  selected.value = r.name;
  detail.submit(
    { doctype: "Test Result", name: r.name },
    {
      onSuccess: (doc) => {
        form.action_status = doc.action_status || "Open";
        form.corrective_action = doc.corrective_action || "";
      },
    }
  );
}

const saveRes = createResource({ url: "frappe.client.set_value" });
function save() {
  saveRes.submit(
    {
      doctype: "Test Result",
      name: selected.value,
      fieldname: JSON.stringify({
        action_status: form.action_status,
        corrective_action: form.corrective_action,
      }),
    },
    { onSuccess: () => results.reload() }
  );
}

const rerunRes = createResource({
  url: "smoke_console.api.rerun",
  onSuccess: (n) => router.push(`/runs/${n}`),
});
const rerunSuite = createResource({
  url: "smoke_console.api.create_and_run",
  onSuccess: (n) => router.push(`/runs/${n}`),
});
function rerunOneSuite() {
  rerunSuite.submit({ site: run.doc.site, test_cases: JSON.stringify([detail.data.suite]) });
}

// Live polling while the run is in flight.
const isRunning = computed(() => RUNNING_STATES.includes(run.doc?.status));
let timer = null;
function ensurePolling() {
  if (timer) return;
  timer = setInterval(() => {
    run.reload();
    results.reload();
    if (!RUNNING_STATES.includes(run.doc?.status)) {
      clearInterval(timer);
      timer = null;
    }
  }, 3000);
}
watch(() => run.doc?.status, (st) => st && RUNNING_STATES.includes(st) && ensurePolling());
onUnmounted(() => timer && clearInterval(timer));
</script>
