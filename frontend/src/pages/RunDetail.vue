<template>
  <div class="max-w-6xl mx-auto p-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-1">
      <button class="text-ink-gray-5 hover:text-ink-gray-8" @click="router.push('/')">←</button>
      <h1 class="text-xl font-semibold">{{ run.doc?.run_title || name }}</h1>
      <Badge :theme="statusTheme(run.doc?.status)" :label="run.doc?.status || '…'" />
      <Badge v-if="run.doc?.layer === 'UI'" theme="blue" label="UI" />
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

    <!-- Output / log first (full width) -->
    <div v-if="run.doc?.log" class="border rounded-lg mb-4">
      <div class="px-3 py-2 text-xs font-medium text-ink-gray-5 uppercase">Output / log</div>
      <pre class="m-0 rounded-b-lg bg-gray-900 text-gray-100 font-mono text-xs p-3 max-h-72 overflow-auto whitespace-pre-wrap">{{ run.doc.log }}</pre>
    </div>

    <!-- Left: suite queue · Right: selected suite detail -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="border rounded-lg divide-y self-start">
        <div class="px-3 py-2 text-xs font-medium text-ink-gray-5 uppercase">Test suites</div>
        <button
          v-for="it in queue"
          :key="it.suite"
          class="w-full text-left flex items-center gap-3 p-3"
          :class="[
            it.result ? 'hover:bg-surface-gray-1 cursor-pointer' : 'cursor-default',
            selected === it.result && it.result ? 'bg-surface-gray-2' : '',
          ]"
          @click="it.result && select(it)"
        >
          <span class="w-5 text-center text-base leading-none" :class="glyphClass(it.status)">
            <span v-if="it.status === 'Running'" class="inline-block animate-spin">◌</span>
            <span v-else>{{ glyph(it.status) }}</span>
          </span>
          <span class="flex-1 font-medium">{{ it.suite }}</span>
          <span v-if="it.duration_ms" class="text-xs text-ink-gray-4">{{ it.duration_ms }} ms</span>
          <span v-else class="text-xs text-ink-gray-4">{{ it.status }}</span>
        </button>
        <div v-if="!queue.length" class="p-4 text-sm text-ink-gray-5">
          {{ isRunning ? "Queueing…" : "No suites." }}
        </div>
      </div>

      <div class="border rounded-lg self-start">
        <div v-if="!detail.data" class="p-6 text-sm text-ink-gray-5">
          Select a completed suite to see its steps and output.
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

          <div class="p-3 space-y-2 bg-surface-gray-1">
            <div class="text-xs font-medium text-ink-gray-5 uppercase">Next actionable</div>
            <FormControl
              type="select"
              label="Action status"
              :options="['Open', 'Investigating', 'Resolved', 'Not Required']"
              v-model="form.action_status"
            />
            <FormControl type="textarea" label="Corrective action" v-model="form.corrective_action" />
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
import { computed, onUnmounted, reactive, ref } from "vue";
import { Badge, Button, createDocumentResource, createResource } from "frappe-ui";
import { useRouter } from "vue-router";
import { statusTheme, RUNNING_STATES } from "@/lib/status";

const props = defineProps({ name: String });
const router = useRouter();
const name = props.name;

const run = createDocumentResource({ doctype: "Release Test", name, auto: true });
const progress = createResource({
  url: "release_manager.api.run_progress",
  params: { run: name },
  auto: true,
});
const queue = computed(() => progress.data?.items || []);

const selected = ref(null);
const detail = createResource({ url: "frappe.client.get" });
const form = reactive({ action_status: "Open", corrective_action: "" });

function select(it) {
  selected.value = it.result;
  detail.submit(
    { doctype: "Test Result", name: it.result },
    {
      onSuccess: (doc) => {
        form.action_status = doc.action_status || "Open";
        form.corrective_action = doc.corrective_action || "";
      },
    }
  );
}

// Frappe-Cloud-style status glyphs for the queue.
function glyph(status) {
  return { Passed: "✓", Failed: "✕", Partial: "●", Skipped: "–", Queued: "○" }[status] || "○";
}
function glyphClass(status) {
  return (
    {
      Passed: "text-ink-green-3",
      Failed: "text-ink-red-3",
      Partial: "text-ink-amber-3",
      Running: "text-ink-blue-3",
      Skipped: "text-ink-gray-4",
      Queued: "text-ink-gray-4",
    }[status] || "text-ink-gray-4"
  );
}

const saveRes = createResource({ url: "frappe.client.set_value" });
function save() {
  saveRes.submit({
    doctype: "Test Result",
    name: selected.value,
    fieldname: JSON.stringify({
      action_status: form.action_status,
      corrective_action: form.corrective_action,
    }),
  });
}

const rerunRes = createResource({
  url: "release_manager.api.rerun",
  onSuccess: (n) => router.push(`/runs/${n}`),
});
const rerunSuite = createResource({
  url: "release_manager.api.create_and_run",
  onSuccess: (n) => router.push(`/runs/${n}`),
});
function rerunOneSuite() {
  rerunSuite.submit({ site: run.doc.site, test_cases: JSON.stringify([detail.data.suite]) });
}

// Live polling while the run is in flight.
const isRunning = computed(() => RUNNING_STATES.includes(run.doc?.status));
const timer = setInterval(() => {
  run.reload();
  progress.reload();
}, 3000);
onUnmounted(() => clearInterval(timer));
</script>
