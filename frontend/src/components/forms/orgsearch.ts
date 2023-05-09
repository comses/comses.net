import BaseControl from "../forms/base";
import { Component, Prop } from "vue-property-decorator";
import axios from "axios";
import _ from "lodash-es";

import Multiselect from "vue-multiselect";

const debounceFetchOrgs = _.debounce(async (self: OrganizationSearch, query: string) => {
  try {
    self.isLoading = true;
    const encoded = encodeURIComponent(query);
    // note: ror rest api has a rate limit of 2000 requests / 5 minute period
    // this should be fine unless things really slow down with periods of high traffic
    // options: self host the rest api, diy it with their data dump + our elasticsearch
    const response = await axios.get("https://api.ror.org/organizations?query=" + encoded);
    const data = response.data;
    const orgs = data.items.map((item: any) => {
      return {
        name: item.name,
        url: item.links[0],
        acronym: item.acronyms[0],
        ror_id: item.id,
      };
    });
    self.orgs = orgs;
    self.isLoading = false;
  } catch (err) {
    self.localErrors = "Error fetching organizations";
    self.isLoading = false;
  }
}, 600);

@Component({
  template: `<div :class="{ 'child-is-invalid': isInvalid }">
    <slot v-if="label" name="label" :label="label">
      <label class="form-control-label">{{ label }}</label>
    </slot>
    <multiselect
      :value="value"
      @input="updateValue"
      :multiple="false"
      label="name"
      track-by="name"
      :allow-empty="true"
      placeholder="Type to find your organization"
      :options="orgs"
      :disabled="disabled"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :options-limit="50"
      :close-on-select="true"
      :limit="50"
      @search-change="fetchOrgs"
    >
      <template slot="noOptions">No results found.</template>
      <template v-slot:caret="{toggle}">
        <span class="multiselect__search-toggle">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </span>
      </template>
      <template slot="option" slot-scope="props">
        <div class="option__desc">
          <span class="option__title">{{ props.option.name }}</span>
          <br />
          <span class="text-muted"
            ><small>{{ props.option.url }}</small></span
          >
        </div>
      </template>
    </multiselect>
    <div v-if="isInvalid" class="invalid-feedback">
      {{ localErrors }}
    </div>
    <slot v-if="help" name="help" :help="help">
      <small class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
  components: {
    Multiselect,
  },
})
export default class OrganizationSearch extends BaseControl {
  @Prop({ default: "" })
  public label: string;

  @Prop({ default: "" })
  public help: string;

  @Prop({ default: false })
  public disabled: boolean;

  public selected: [] | object;

  public isLoading = false;
  public orgs = [];
  public localErrors: string = "";

  public fetchOrgs(query) {
    if (query.length > 1) {
      debounceFetchOrgs.cancel();
      debounceFetchOrgs(this, query);
    }
  }

  public updateValue(value) {
    this.localErrors = "";
    this.$emit("input", value);
  }
}
