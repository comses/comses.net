<template>
    <div :class="['form-group', {'has-danger': hasDanger }]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
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
                :limit="20"
                @search-change="fetchMatchingTags">
        </multiselect>
        <div class="form-control-feedback form-control-danger">
            {{ errorMessage }}
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
    import {api} from '../api/index'

    import Multiselect from 'vue-multiselect'

    @Component({
        components: {
            Multiselect
        }
    })
    export default class Tagger extends BaseControl {
        @Prop({default: 'Type to find matching tags'})
        placeholder: string;

        @Prop
        label: string;

        @Prop
        help: string;

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
