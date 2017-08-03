<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label"></slot>
        <multiselect
                :value="value"
                @input="updateValue"
                label="name"
                track-by="name"
                placeholder="Type to find keywords"
                :options="matchingTags"
                :multiple="true"
                :loading="isLoading"
                :searchable="true"
                :internal-search="false"
                :clear-on-select="false"
                :close-on-select="false"
                :options-limit="50"
                :limit="20"
                @search-change="fetchMatchingTags">
        </multiselect>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
        </div>
        <slot name="help"></slot>
    </div>
</template>
<script lang="ts">
    import BaseControl from './forms/base'
    import {Component, Prop} from 'vue-property-decorator'

    import * as queryString from 'query-string'
    import {api} from '../api/index'

    import Multiselect from 'vue-multiselect'

    @Component({
        components: {
            Multiselect
        }
    })
    export default class Tagger extends BaseControl {
        isLoading = false;
        matchingTags = [];

        fetchMatchingTags(query) {
            this.isLoading = true;
            api.tags.list({query, page: 1})
                    .then(state => {
                        this.matchingTags = state.results;
                        this.isLoading = false;
                    })
                    .catch(err => {
                        this.isLoading = false;
                    });
        }

        updateValue(value) {
            let self: any = this;
            this.$emit('input', value);
            this.$emit('clear', this.name);
        }
    }
</script>
