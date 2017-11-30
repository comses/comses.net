
import BaseControl from './forms/base'
import {Component, Prop} from 'vue-property-decorator'

import * as queryString from 'query-string'
import * as _ from 'lodash'
import {ProfileAPI} from 'api'

import Multiselect from 'vue-multiselect'

const profileAPI = new ProfileAPI();

const debounceFetchMatchingUsers = _.debounce((self: UsernameSearch, query: string) => {
    self.isLoading = true;
    profileAPI.search({query, page: 1})
            .then(response => {
                self.matchingUsers = response.data.results;
                self.isLoading = false;
            })
            .catch(err => {
                self.localErrors = 'Error fetching tags';
                self.isLoading = false;
            });
}, 600);

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
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
                @search-change="fetchMatchingUsers">
        </multiselect>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ [errorMessage, localErrors].filter(msg => msg !== '').join(', ') }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        Multiselect
    }
})
export default class UsernameSearch extends BaseControl {
    @Prop({default: ''})
    label: string;

    @Prop({default: ''})
    help: string;

    isLoading = false;
    matchingUsers = [];
    localErrors: string = '';

    displayInfo(userInfo) {
        let displayName: string = userInfo.full_name;
        if (userInfo.full_name !== userInfo.username) {
            displayName = `${userInfo.full_name} (${userInfo.username})`;
        }
        return `${displayName}${userInfo.institution_name ? `, ${userInfo.institution_name}` : ''}`;
    }

    fetchMatchingUsers(query) {
        debounceFetchMatchingUsers.cancel();
        debounceFetchMatchingUsers(this, query);
    }

    updateValue(value) {
        this.localErrors = '';
        this.$emit('input', value);
    }
}
