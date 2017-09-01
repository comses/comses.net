import BaseControl from './forms/base'
import {Component, Prop} from 'vue-property-decorator'
import * as _ from 'lodash'

import * as queryString from 'query-string'
import {tagAPI} from 'api'

import Multiselect from 'vue-multiselect'

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
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
                :taggable="true"
                :limit="20"
                @tag="addTag"
                @search-change="fetchMatchingTags">
        </multiselect>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ errorMessage }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
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

    addTag(name, id) {
        this.updateValue(_.concat(this.value, [{ name}]));
    }

    async fetchMatchingTags(query) {
        this.isLoading = true;
        const response = await tagAPI.list({query, page: 1});
        this.matchingTags = response.data.results;
        this.isLoading = false;
    }

    updateValue(value) {
        let self: any = this;
        this.$emit('input', value);
        this.$emit('clear', this.name);
    }
}