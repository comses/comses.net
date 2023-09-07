<template>
  <div
    class="modal fade"
    :id="id"
    tabindex="-1"
    :aria-labelledby="`${id}-label`"
    aria-hidden="true"
    ref="modalElement"
  >
    <div
      :class="[
        'modal-dialog',
        modalSizeClass,
        centered ? 'modal-dialog-centered' : '',
        scrollable ? 'modal-dialog-scrollable' : '',
      ]"
    >
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" :id="`${id}-label`">
            {{ title || "" }}
            <slot name="afterTitle" />
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <slot name="content">
          <div class="modal-body">
            <slot name="body" />
          </div>
          <div class="modal-footer border-0">
            <slot name="footer">
              <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">
                Close
              </button>
            </slot>
          </div>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import Modal from "bootstrap/js/dist/modal";

export interface BootstrapModalProps {
  id: string;
  title?: string;
  centered?: boolean;
  scrollable?: boolean;
  size?: "sm" | "md" | "lg" | "xl";
}

const props = withDefaults(defineProps<BootstrapModalProps>(), {
  centered: false,
  size: "md",
});

const modalElement = ref<Element>();
let modal: Modal;

onMounted(() => {
  modal = new Modal(modalElement.value!);
});

onUnmounted(() => {
  modal.dispose();
  modal = null!;
});

defineExpose({
  show: () => {
    modal.show();
  },
  hide: () => {
    modal.hide();
  },
});

const modalSizeClass = computed(() => {
  return props.size === "md" ? "" : `modal-${props.size}`;
});
</script>
