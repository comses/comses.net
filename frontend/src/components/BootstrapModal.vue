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

const emit = defineEmits(["show", "shown", "hide", "hidden"]);

const modalElement = ref<Element>();
let modal: Modal;

const onShow = () => emit("show");
const onShown = () => emit("shown");
const onHide = () => emit("hide");
const onHidden = () => emit("hidden");

onMounted(() => {
  const el = modalElement.value;
  if (!el) return;

  modal = new Modal(el);

  el.addEventListener("show.bs.modal", onShow);
  el.addEventListener("shown.bs.modal", onShown);
  el.addEventListener("hide.bs.modal", onHide);
  el.addEventListener("hidden.bs.modal", onHidden);
});

onUnmounted(() => {
  const el = modalElement.value;
  if (!el) return;

  el.removeEventListener("show.bs.modal", onShow);
  el.removeEventListener("shown.bs.modal", onShown);
  el.removeEventListener("hide.bs.modal", onHide);
  el.removeEventListener("hidden.bs.modal", onHidden);

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
