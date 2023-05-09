import BaseControl from "./forms/base";
import { Component, Prop } from "vue-property-decorator";
import _ from "lodash-es";
import Multiselect from "vue-multiselect";
import { TagAPI } from "@/api";

@Component({
  template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
    <slot name="label" :label="label">
      <label :class="['form-control-label', requiredClass]">{{ label }}</label>
    </slot>
    <multiselect
      :value="value"
      @input="updateValue"
      label="name"
      track-by="name"
      :placeholder="placeholder"
      :options="matchingTags"
      :multiple="true"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :clear-on-select="false"
      :close-on-select="false"
      :options-limit="50"
      :taggable="true"
      :limit="20"
      @tag="addTag"
      @search-change="fetchMatchingTags"
    >
    </multiselect>
    <div v-if="isInvalid" class="invalid-feedback">
      {{ errorMessage }}
    </div>
    <slot name="help" :help="help">
      <small class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
  components: {
    Multiselect,
  },
})
export default class Tagger extends BaseControl {
  @Prop({ default: "Type to find matching tags" })
  public placeholder: string;

  @Prop()
  public label: string;

  @Prop()
  public help: string;

  public isLoading = false;
  public matchingTags = [];

  public addTag(name, id) {
    this.updateValue(_.concat(this.value, [{ name }]));
  }

  public list(query) {
    return TagAPI.list({ query });
  }

  public async fetchMatchingTags(query) {
    this.isLoading = true;
    const response = await this.list(query);
    this.matchingTags = response.data.results;
    this.isLoading = false;
  }

  public updateValue(value) {
    this.$emit("input", value);
    this.$emit("clear", this.name);
  }
}

export class EventTagger extends Tagger {
  public list(query) {
    return TagAPI.listEventTags({ query });
  }
}

export class JobTagger extends Tagger {
  public list(query) {
    return TagAPI.listJobTags({ query });
  }
}

export class CodebaseTagger extends Tagger {
  public list(query) {
    return TagAPI.listCodebaseTags({ query });
  }
}

export class ProfileTagger extends Tagger {
  public list(query) {
    return TagAPI.listProfileTags({ query });
  }
}
