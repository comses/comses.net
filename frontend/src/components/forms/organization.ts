import BaseControl from '../forms/base';
import {Component, Prop} from 'vue-property-decorator';
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
                :value="value"
                @input="updateValue"
                :multiple="multiple"
                label="name"
                track-by="name"
                :custom-label="displayInfo"
                :allow-empty="false"
                deselect-label=""
                placeholder="Type to find your organization"
                :options="orgs"
                :loading="isLoading"
                :searchable="true"
                :internal-search="false"
                :options-limit="50"
                :limit="20"
                @search-change="fetchOrgs">
        </multiselect>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ [errorMessage, localErrors].filter(msg => msg !== '').join(', ') }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
        <!-- TODO: remove or figure out how add custom org functionality -->
        <!-- <button type="button" class="btn btn-link p-0" @click="showCustom = !showCustom">
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
export default class OrganizationSearch extends BaseControl {
    @Prop({default: ''})
    public label: string;

    @Prop({default: ''})
    public help: string;

    @Prop({default: false})
    public multiple: boolean;

    public isLoading = false;
    public orgs = [];
    public localErrors: string = '';

    public displayInfo(org) {
        if (!org.name) {
            return null;
        } else {
            return `${org.name} (${org.url})`;
        }
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
