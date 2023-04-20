<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="indicateRequired" />
    </slot>
    <div class="form-check-inline ms-3">
      <label class="form-check-label" :for="`${id}-custom-input-check`">
        <input
          type="checkbox"
          class="form-check-input me-1"
          v-model="showCustomInput"
          :id="`${id}-custom-input-check`"
        />
        <small class="text-muted">Enter manually</small>
      </label>
    </div>
    <FormPlaceholder v-if="showPlaceholder" />
    <span v-else-if="showCustomInput">
      <div class="input-group">
        <input
          v-model="candidateCustomName"
          :id="`${id}-custom-input-name`"
          :class="['form-control', { 'is-invalid': localErrors.name }]"
          placeholder="Name (ex. Arizona State University)"
          @input="localErrors.name = ''"
          @keydown.enter.prevent="createCustom"
        />
        <input
          v-model="candidateCustomUrl"
          :id="`${id}-custom-input-url`"
          :class="['form-control', { 'is-invalid': localErrors.url }]"
          placeholder="URL (ex. http://asu.edu)"
          @input="localErrors.url = ''"
          @keydown.enter.prevent="createCustom"
        />
        <button
          type="button"
          v-if="candidateCustomName || candidateCustomUrl"
          class="btn btn-outline-secondary"
          @click="createCustom"
        >
          <small>Press enter to add</small>
        </button>
      </div>
      <FormError
        v-if="localErrors.name || localErrors.url"
        :error="localErrorMessage"
        :id-for="id"
      />
    </span>
    <FormOrgSearch v-else name="organization" :clear-on-select="true" @select="create" />
    <Sortable :list="value" :item-key="item => item" @end="sort($event)">
      <template #item="{ element, index }">
        <div :key="element" class="my-1 input-group">
          <span class="primary-group-button">
            <button v-if="index === 0" type="button" class="btn btn-is-primary w-100">
              Primary
            </button>
            <button
              v-else
              type="button"
              class="btn btn-make-primary w-100"
              @click="sortToTop(index)"
            >
              <small>Set primary</small>
            </button>
          </span>
          <input :value="element.name" class="form-control w-25" readonly />
          <span class="input-group-text bg-white flex-grow-1 flex-shrink-1 w-25">
            <a :href="element.url">{{ element.url }}</a>
          </span>
          <button
            type="button"
            class="btn btn-delete-item"
            tabindex="-1"
            @click.once="remove(index)"
          >
            &times;
          </button>
        </div>
      </template>
    </Sortable>
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { inject, ref, onMounted, reactive, computed } from "vue";
import { string } from "yup";
import { Sortable } from "sortablejs-vue3";
import type { SortableEvent } from "sortablejs";
import { useField } from "@/composables/form";
import FormOrgSearch from "@/components/form/FormOrgSearch.vue";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import type { Organization } from "@/composables/api/ror";

export interface TextItemsProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  indicateRequired?: boolean;
}

const props = defineProps<TextItemsProps>();

onMounted(() => {
  if (!value.value) {
    // force initialize to empty array
    value.value = [];
  }
});

const showCustomInput = ref(false);
const candidateCustomName = ref("");
const candidateCustomUrl = ref("");
const localErrors = reactive({ name: "", url: "" });

const localErrorMessage = computed(() => {
  return `${localErrors.name}
          ${localErrors.name && localErrors.url ? "and " : ""}
          ${localErrors.url}`;
});

function validateLocal() {
  let valid = true;
  if (!candidateCustomName.value) {
    localErrors.name = "Affiliation name is required";
    valid = false;
  }
  const schema = string().url();
  if (!schema.isValidSync(candidateCustomUrl.value)) {
    localErrors.url = "Affiliation URL must be a valid URL";
    valid = false;
  }
  if (!candidateCustomUrl.value) {
    localErrors.url = "Affiliation URL is required";
    valid = false;
  }
  return valid;
}

function createCustom() {
  if (validateLocal()) {
    const customOrg: Organization = {
      name: candidateCustomName.value,
      url: candidateCustomUrl.value,
    };
    create(customOrg);
    candidateCustomName.value = "";
    candidateCustomUrl.value = "";
  }
}

function create(organization: Organization) {
  if (!value.value.some(e => e.name === organization.name)) {
    value.value.push(organization);
  }
}

function remove(index: number) {
  value.value.splice(index, 1);
}

function sort(event: SortableEvent) {
  const { newIndex, oldIndex } = event;
  if (newIndex !== undefined && oldIndex !== undefined) {
    const item = value.value.splice(oldIndex, 1)[0];
    value.value.splice(newIndex, 0, item);
  }
}

function sortToTop(index: number) {
  const item = value.value.splice(index, 1)[0];
  value.value.splice(0, 0, item);
}

const { id, value, error } = useField<Organization[]>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
