import BaseControl from "./forms/base";
import { Component, Prop } from "vue-property-decorator";
import _ from "lodash-es";
import { ProfileAPI } from "@/api";

import Multiselect from "vue-multiselect";

const profileAPI = new ProfileAPI();

const debounceFetchMatchingUsers = _.debounce(async (self: UsernameSearch, query: string) => {
  try {
    self.isLoading = true;
    const response = await profileAPI.search({ query, page: 1 });
    self.matchingUsers = response.data.results;
    console.log(self.matchingUsers);
    self.isLoading = false;
  } catch (err) {
    self.localErrors = "Error fetching tags";
    self.isLoading = false;
  }
}, 600);

@Component({
  template: `<div :class="['mb-3', {'child-is-invalid': isInvalid }]">
    <slot name="label" :label="label">
      <label class="form-label">{{ label }}</label>
    </slot>
    <multiselect
      :value="value"
      @input="updateValue"
      label="username"
      track-by="username"
      :custom-label="displayInfo"
      placeholder="Type to find users"
      :options="matchingUsers"
      :multiple="false"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingUsers"
    >
    </multiselect>
    <div v-if="isInvalid" class="invalid-feedback">
      {{ [errorMessage, localErrors].filter(msg => msg !== '').join(', ') }}
    </div>
    <slot name="help" :help="help">
      <small class="form-text text-muted">{{ help }}</small>
    </slot>
  </div>`,
  components: {
    Multiselect,
  },
})
export default class UsernameSearch extends BaseControl {
  @Prop({ default: "" })
  public label: string;

  @Prop({ default: "" })
  public help: string;

  public isLoading = false;
  public matchingUsers = [];
  public localErrors: string = "";

  public displayInfo(userInfo) {
    let displayName: string = userInfo.name;
    if (userInfo.name !== userInfo.username) {
      displayName = `${userInfo.name} (${userInfo.username})`;
    }
    return `${displayName}${userInfo.institution_name ? `, ${userInfo.institution_name}` : ""}`;
  }

  public fetchMatchingUsers(query) {
    debounceFetchMatchingUsers.cancel();
    debounceFetchMatchingUsers(this, query);
  }

  public updateValue(value) {
    this.localErrors = "";
    this.$emit("input", value);
  }
}
