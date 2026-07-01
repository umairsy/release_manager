<template>
  <div class="p-6 max-w-lg mx-auto">
    <div class="flex items-center gap-2 mb-4">
      <button class="text-ink-gray-5 hover:text-ink-gray-8" @click="router.back()">←</button>
      <h1 class="text-xl font-semibold">New Smoke Run</h1>
    </div>

    <div class="space-y-4">
      <FormControl
        type="select"
        label="Site"
        :options="siteOptions"
        v-model="site"
      />
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
      <ErrorMessage :message="create.error" />
      <Button variant="solid" :loading="create.loading" :disabled="!site" @click="run">
        Run
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { createListResource, createResource, ErrorMessage } from "frappe-ui";
import { useRouter } from "vue-router";

const router = useRouter();
const site = ref("");
const group = ref("");

const sites = createListResource({
  doctype: "Smoke Site",
  fields: ["name"],
  filters: { enabled: 1 },
  pageLength: 100,
  auto: true,
});
const groups = createListResource({
  doctype: "Smoke Test Group",
  fields: ["name"],
  filters: { enabled: 1 },
  pageLength: 100,
  auto: true,
});

const siteOptions = computed(() => (sites.data || []).map((s) => s.name));
const groupOptions = computed(() => ["", ...(groups.data || []).map((g) => g.name)]);

const create = createResource({
  url: "smoke_console.api.create_and_run",
  onSuccess: (name) => router.push(`/runs/${name}`),
});

function run() {
  if (!site.value) return;
  create.submit({ site: site.value, group: group.value || null });
}
</script>
