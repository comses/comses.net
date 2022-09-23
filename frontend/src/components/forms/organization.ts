import BaseControl from '../forms/base';
import { Component, Prop, ModelSync } from 'vue-property-decorator';
import * as queryString from 'query-string';
import * as _ from 'lodash';

import Multiselect from 'vue-multiselect';

// TODO: fix missing CORS header
const debounceFetchOrgs = _.debounce(async (self: OrganizationSearch, query: string) => {
    try {
        self.isLoading = true;
        let encoded = encodeURIComponent(query);
        const response = await fetch("https://api.ror.org/organizations?affiliation=" + encoded);
        const data = await response.json();
        const orgs = data.items.map((item: any) => {
            return {
                name: item.organization.name,
                url: item.organization.links[0],
                acronym: item.organization.acronyms[0],
                ror_id: item.organization.id,
            }
        });
        self.orgs = orgs;
        self.isLoading = false;
    } catch (err) {
        self.localErrors = 'Error fetching organizations';
        self.isLoading = false;
    }
}, 600);

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
        </slot>
        <multiselect
                v-model="selectedLocal"
                @input="updateValue"
                :multiple="multiple"
                label="name"
                track-by="name"
                :allow-empty="true"
                placeholder="Type to find your organization"
                :options="orgs"
                :loading="isLoading"
                :searchable="true"
                :internal-search="false"
                :options-limit="50"
                :close-on-select="!multiple"
                :max="20"
                :limit="20"
                @search-change="fetchOrgs">
            <template slot="clear" slot-scope="props" v-if="selectedLocal">
                <div class="multiselect__clear" title="Clear selection" @mousedown.prevent.stop="selectedLocal=null">
                    &times;
                </div>
            </template>
            <template slot="option" slot-scope="props">
                <div class="option__desc"><span class="option__title">{{ props.option.name }}</span>
                <br>
                <span class="text-muted"><small>{{ props.option.url }}</small></span></div>
            </template>
        </multiselect>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ localErrors ? localErrors : "Affiliation is a required field" }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
        <!-- TODO: remove or figure out how add custom org functionality -->
        <!-- <button type="button" class="btn btn-link align-baseline p-0" @click="showCustom = !showCustom">
            <small class="form-text">
                <i class="fas fa-chevron-down" v-if="!showCustom"></i>
                <i class="fas fa-chevron-up" v-else></i>
                 Can't find your organization?
            </small>
        </button>
        -->
    </div>`,
    components: {
        Multiselect,
    },
})

// TODO: style multiselect components to be consistent with other bootstrap selects
export default class OrganizationSearch extends BaseControl {
    @Prop({default: ''})
    public label: string;

    @Prop({default: ''})
    public help: string;

    @Prop({default: false})
    public multiple: boolean;

    @Prop()
    public selectedOrgs: any;

    @ModelSync('selectedOrgs', 'input')
    readonly selectedLocal!: any;

    public isLoading = false;
    public orgs = [];
    public localErrors: string = '';

    public clearAll() {
        this.selectedOrgs = [];
    }

    public fetchOrgs(query) {
        if (query.length > 5) {
            debounceFetchOrgs.cancel();
            debounceFetchOrgs(this, query);
        }
    }

    public updateValue(value) {
        this.localErrors = '';
        this.$emit('input', value);
    }
}
