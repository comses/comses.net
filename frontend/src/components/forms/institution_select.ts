import BaseControl from './base';
import {Component, Prop} from 'vue-property-decorator';
import * as _ from 'lodash';
import Multiselect from 'vue-multiselect';
import {TagAPI} from '@/api';

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <multiselect
            :value="value"
            :label="value"
            track-by="value"
            :placeholder="placeholder"
            :options="orgs"
            :multiple="true"
            :loading="isLoading"
            :searchable="true"
            :internal-search="false"
            :clear-on-select="false"
            :close-on-select="false"
            @search-change="fetchOrgs">
        </multiselect>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ errorMessage }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        Multiselect,
    },
})
class InstitutionSelect extends BaseControl {
    @Prop({default: 'Search for institution'})
    public placeholder: string;

    @Prop()
    public label: string;

    @Prop({default: null})
    public help: string;

    public isLoading = false;

    public orgs = [];

    public addTag(name, id) {
        this.updateValue(_.concat(this.value, [{ name}]));
    }

    public list(query) {
        return TagAPI.list({query});
    }

    public async fetchOrgs(query: string) {
        //temp
        if (query.length < 5) return;
        let encoded = encodeURIComponent(query);
        const response = await fetch("https://api.ror.org/organizations?affiliation=" + encoded);
        const data = await response.json();
        const orgs = data.items.map((item: any) => {
            return { value: item.organization.name,
                     url: item.organization.links[0]
            }
        })
        this.orgs = orgs;
    }


    public updateValue(value) {
        const self: any = this;
        this.$emit('input', value);
        this.$emit('clear', this.name);
    }
}

export default InstitutionSelect;