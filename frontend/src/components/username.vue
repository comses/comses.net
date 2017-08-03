<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
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
        <div class="form-control-feedback form-control-danger">
            {{ [errorMessage, localErrors].filter(msg => msg !== '').join(', ') }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>
</template>
<script lang="ts">
    import BaseControl from './forms/base'
    import {Component, Prop} from 'vue-property-decorator'

    import * as queryString from 'query-string'
    import * as _ from 'lodash'
    import {api_base} from '../api/index'

    import Multiselect from 'vue-multiselect'

    const debounceFetchMatchingUsers = _.debounce((self: UsernameSearch, query: string) => {
        self.isLoading = true;
        api_base.get(`/users/?${queryString.stringify({query, page: 1})}`)
                .then(response => {
                    self.matchingUsers = response.data.results;
                    self.isLoading = false;
                })
                .catch(err => {
                    self.localErrors = 'Error fetching tags';
                    self.isLoading = false;
                });
    }, 800);

    @Component({
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
            return `${userInfo.full_name}${userInfo.institution_name ? `, ${userInfo.institution_name}` : ''}`;
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
</script>
