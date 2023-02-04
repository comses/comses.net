import { Component, Prop } from "vue-property-decorator";
import Vue from "vue";
import Multiselect from "vue-multiselect";
import { ReviewEditorAPI } from "@/api";
import * as _ from "lodash";
import { holder } from "@/pages/review/directives";

const reviewApi = new ReviewEditorAPI();

const debounceFetchMatchingUsers = _.debounce(async (self: ReviewerFinder, query: string) => {
  try {
    self.isLoading = true;
    const response = await reviewApi.findReviewers({ query });
    self.matchingUsers = response.data.results;
    self.isLoading = false;
  } catch (err) {
    self.localErrors = "Error fetching tags";
    self.isLoading = false;
  }
}, 600);

@Component({
  template: `<multiselect
    :value="value"
    @input="updateValue"
    label="username"
    track-by="username"
    placeholder="Find a reviewer"
    :options="matchingUsers"
    :multiple="false"
    :loading="isLoading"
    :searchable="true"
    :internal-search="false"
    :options-limit="50"
    :limit="20"
    @search-change="fetchMatchingUsers"
  >
    <template slot="option" slot-scope="props">
      <div class="container">
        <div class="row">
          <div class="col-2">
            <img
              :src="props.option.avatar_url"
              class="img-fluid img-thumbnail"
              alt="No picture available"
            />
          </div>
          <div class="col-10">
            <h2>{{ props.option.name }}</h2>
            <div class="tag-list">
              <div class="tag mx-1" v-for="tag in props.option.tags">{{ tag.name }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </multiselect>`,
  components: {
    Multiselect,
  },
  directives: {
    holder,
  },
})
export class ReviewerFinder extends Vue {
  @Prop()
  public value;

  public isLoading = false;
  public localErrors = "";
  public matchingUsers = [];

  public fetchMatchingUsers(query) {
    debounceFetchMatchingUsers.cancel();
    debounceFetchMatchingUsers(this, query);
  }

  public updateValue(value) {
    this.localErrors = "";
    this.$emit("input", value);
  }
}
