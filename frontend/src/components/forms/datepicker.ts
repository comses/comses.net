import { Component, Prop } from "vue-property-decorator";
import BaseControl from "./base";
import Datepicker from "vuejs-datepicker";
import * as _ from "lodash";

@Component({
  template: `<div class="mb-3">
    <slot name="label">
      <label :class="['form-label', requiredClass]">{{ label }}</label>
    </slot>
    <datepicker
      :bootstrap-styling="true"
      :value="dateValue"
      @input="updateDate"
      wrapper-class="comses-datepicker"
      :format="format"
      :input-class="datepickerInputClass"
      clear-button-icon="fas fa-times"
      :clear-button="clearButton"
      :open-date="openDate"
      @cleared="cleared"
    >
    </datepicker>
    <div v-if="isInvalid" class="invalid-feedback-always">{{ errorMessage }}</div>
    <slot name="help">
      <small class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
  components: {
    datepicker: Datepicker,
  },
})
export default class InputDatepicker extends BaseControl {
  @Prop()
  public label: string;

  @Prop()
  public help: string;

  @Prop()
  public formatString: string;

  @Prop({ default: false })
  public clearButton: boolean;

  @Prop()
  public openDate: string | Date;

  get format() {
    return _.isEmpty(this.formatString) ? "yyyy-MM-dd" : this.formatString;
  }

  get datepickerInputClass() {
    return this.isInvalid ? "is-invalid" : "";
  }

  get dateValue() {
    // Otherwise displayed date is off by one https://github.com/charliekassel/vuejs-datepicker/issues/158
    if (_.isEmpty(this.value)) {
      return null;
    }
    const [yearStr, monthStr, dayStr] = this.value.split("-");
    const year = parseInt(yearStr);
    const month = parseInt(monthStr) - 1; // month argument is zero indexed so 0 is January
    const day = parseInt(dayStr.split("T")[0]);
    return new Date(year, month, day);
  }

  public updateDate(value) {
    if (_.isNil(value)) {
      this.updateValue(value);
    } else {
      switch (value.constructor.name) {
        case "String":
          this.updateValue(value);
          break;
        case "Date":
          this.updateValue(value.toISOString());
          break;
        default:
          throw Error(`invalid type ${value.constructor.name} in date field`);
      }
    }
  }

  public cleared() {
    this.updateValue(null);
  }
}
