import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import Multiselect from 'vue-multiselect'
import {ProfileAPI, ReviewEditorAPI} from "api";
import * as _ from 'lodash';

const reviewApi = new ReviewEditorAPI();
const profileApi = new ProfileAPI();

const debounceFetchMatchingUsers = _.debounce(async (self: ReviewerFinder, query: string) => {
    try {
        self.isLoading = true;
        const response = await profileApi.search({query, page: 1});
        self.matchingUsers = response.data.results;
        self.isLoading = false;
    } catch (err) {
        self.localErrors = 'Error fetching tags';
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
                @search-change="fetchMatchingUsers">
            <template slot="option" slot-scope="props">
                <div class="container">
                    <div class="row">
                        <div class="col-2">
                            <img v-holder="props.option.avatar">
                        </div>
                        <div class="col-10">
                            <h2>{{ props.option.full_name }}</h2>
                            <div class="tag-list">
                                <div class="tag mx-1" v-for="tag in props.option.tags">{{ tag.name }}</div>
                            </div>
                        </div>
                    </div>
                </div>            
            </template>
        </multiselect>`,
    components: {
        Multiselect
    },
    directives: {
        holder: {
            update(el, binding) {
                if (!binding.expression) {
                    throw new Error('holder directive must have a value')
                }
                if (_.isNull(binding.value)) {
                    el.setAttribute('src', undefined);
                    el.setAttribute('data-src', 'holder.js/80x80?text=No submitted image');
                    Holder.run({
                        images: el
                    });
                } else {
                    el.setAttribute('src', binding.value);
                }
            }
        }
    }
})
export class ReviewerFinder extends Vue {
    @Prop()
    value;

    isLoading = false;
    localErrors = '';
    matchingUsers = [];

    fetchMatchingUsers(query) {
        debounceFetchMatchingUsers.cancel();
        debounceFetchMatchingUsers(this, query);
    }

    updateValue(value) {
        this.localErrors = '';
        this.$emit('input', value);
    }
}