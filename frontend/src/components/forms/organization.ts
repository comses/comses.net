import BaseControl from '../forms/base';
import {Component, Prop} from 'vue-property-decorator';
import * as queryString from 'query-string';
import * as _ from 'lodash';

import Multiselect from 'vue-multiselect';

// TODO: fix missing CORS header
const debounceFetchOrgs = _.debounce(async (self: InstitutionSelect, query: string) => {
    try {
        self.isLoading = true;
        let encoded = encodeURIComponent(query);
        const response = await fetch("https://api.ror.org/organizations?affiliation=" + encoded);
        const data = await response.json();
        const orgs = data.items.map((item: any) => {
            return { name: item.organization.name,
                     url: item.organization.links[0],
                     acronym: item.organization.acronyms[0],
                     rorid: item.organization.id,
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
                label="name"
                track-by="name"
                :custom-label="displayInfo"
                :allow-empty="false"
                deselect-label=""
                placeholder="Type to find your organization"
                :options="orgs"
                :multiple="false"
                :loading="isLoading"
                :searchable="true"
                :internal-search="false"
                :options-limit="50"
                :limit="20"
                @search-change="fetchOrgs">
        </multiselect>
        <template slot="singleLabel" slot-scope="props">
            <span class="option__title">{{ props.option.name }}</span></span>
        </template>
        <template slot="option" slot-scope="props">
            <div class="option__desc"><span class="option__title">{{ props.option.name }}</span><span class="option__small">{{ props.option.url }}</span></div>
        </template>
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
export default class OrganizationSearch extends BaseControl {
    @Prop({default: ''})
    public label: string;

    @Prop({default: ''})
    public help: string;

    public isLoading = false;
    public orgs = [];
    public localErrors: string = '';

    public displayInfo(org) {
        return `${org.name} (${org.url})`;
    }

    public fetchOrgs(query) {
        debounceFetchOrgs.cancel();
        debounceFetchOrgs(this, query);
    }

    public updateValue(value) {
        this.localErrors = '';
        this.$emit('input', value);
    }
}
