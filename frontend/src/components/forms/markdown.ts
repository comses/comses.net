import BaseControl from "@/components/forms/base";
import { Component, Prop } from "vue-property-decorator";
import VueEasymde from "vue-easymde";
import "easymde/dist/easymde.min.css";

@Component({
  template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
    <slot name="label" :label="label">
      <label :class="['form-control-label', requiredClass]">
        {{ label }}
      </label>
    </slot>
    <vue-easymde
      @update:modelValue="updateValue"
      :configs="configs"
      :modelValue="value"
      ref="markdownEditor"
    ></vue-easymde>
    <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
    <slot name="help">
      <small :aria-describedby="controlId" class="form-text text-muted">
        {{ help }}
      </small>
    </slot>
  </div>`,
  components: {
    "vue-easymde": VueEasymde,
  },
})
export default class Markdown extends BaseControl {
  @Prop()
  public label: string;

  @Prop()
  public help: string;

  get configs() {
    return {
      placeholder: "Markdown formatting is supported",
      status: false,
      toolbar: [
        "bold",
        "italic",
        "heading",
        "|",
        "code",
        "quote",
        "unordered-list",
        "ordered-list",
        "|",
        "horizontal-rule",
        "link",
        "image",
        "|",
        "preview",
        "|",
        "guide",
      ],
    };
  }

  get easymde() {
    return (this.$refs.markdownEditor as any).easymde;
  }

  public refresh() {
    this.easymde.codemirror.refresh();
  }

  mounted() {
    const codemirror = this.easymde.codemirror;
    codemirror.options.extraKeys.Tab = false;
    codemirror.options.extraKeys["Shift-Tab"] = false;
  }
}
