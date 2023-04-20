<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="indicateRequired" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <div v-else class="input-group">
      <input
        v-model="candidateItem"
        type="text"
        :id="id"
        :placeholder="placeholder"
        v-bind="attrs"
        :class="{ 'form-control': true, 'is-invalid': error, 'border-end-0': !!candidateItem }"
        @keydown.enter.prevent="create"
      />
      <button type="button" v-if="candidateItem" class="btn btn-outline-secondary" @click="create">
        <small>Press enter to add</small>
      </button>
    </div>
    <Sortable :list="value" :item-key="item => item" @end="sort($event)">
      <template #item="{ element, index }">
        <div :key="element" class="my-1 input-group">
          <span class="input-group-text bg-white text-gray" title="Drag entries to sort">
            <i class="fas fa-sort" />
          </span>
          <input :value="element" class="form-control" readonly />
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
import { inject, ref, onMounted } from "vue";
import { Sortable } from "sortablejs-vue3";
import type { SortableEvent } from "sortablejs";
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";

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

function create() {
  if (candidateItem.value && !value.value.includes(candidateItem.value)) {
    value.value.push(candidateItem.value);
    candidateItem.value = "";
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

const candidateItem = ref("");

const { id, value, attrs, error } = useField<string[]>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);
</script>
