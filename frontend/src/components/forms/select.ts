import { Component, Prop } from "vue-property-decorator";
import BaseControl from "./base";

// FIXME: redo custom input
@Component({
  template: `<div class="mb-3">
    <slot name="label">
      <label :for="controlId" :class="['form-label', requiredClass]">{{ label }}</label>
    </slot>
    <select
      :id="controlId"
      :name="name"
      :class="['form-control', 'form-select', {'is-invalid': isInvalid}]"
      @change="updateValue($event.target.value)"
      :value="value"
    >
      <option :value="option.value" :selected="option.value === value" v-for="option in options">
        {{ option.label }}
      </option>
    </select>
    <div class="invalid-feedback">
      {{ errorMessage }}
    </div>
    <slot name="help">
      <small :aria-describedby="controlId" class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
})
export default class Select extends BaseControl {
  @Prop({ default: "" })
  public label: string;

  @Prop({ default: "" })
  public help: string;

  @Prop()
  public options: [{ value: string; label: string }];
}
