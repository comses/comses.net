import {Component, Prop} from 'vue-property-decorator';
import BaseControl from '@/components/forms/base';
import OrganizationSearch from '@/components/forms/orgsearch';
import draggable from 'vuedraggable';
import * as yup from 'yup';

@Component({
    template: `<div class="form-group">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <div class="form-check-inline ml-3">
            <label class="form-check-label">
                <input type="checkbox" class="form-check-input" v-model="customInput">
                <small>Enter manually</small>
            </label>
        </div>
        <div v-if="customInput">
            <div class="input-group">
                <input type="text" :class="['form-control', { 'is-invalid': localErrors.name }]" placeholder="Name"
                    v-model="customName" @input="localErrors.name = ''" @keyup.enter="createCustom">
                <input type="url" :class="['form-control', { 'is-invalid': localErrors.url }]" placeholder="URL (ex. http://website.com/)"
                    v-model="customUrl" @input="localErrors.url = ''" @keyup.enter="createCustom">
                <button type="button" class="btn btn-outline-dark" @click="createCustom">Enter</button>
            </div>
            <div v-if="isValidLocal" class="text-danger">
                <small>{{ localErrorMessage }}</small>
            </div>
        </div>
        <c-org-search v-else
            v-model="candidateItem"
            @input="create"
            :name="name"
            :disabled="false"
        ></c-org-search>
        <draggable :list="value" @start="drag=true" @end="drag=false">
            <div v-for="(item, index) in value" :key="index" class="input-group my-1">
                <span class="primary-group-button">
                <button v-if="index === 0" type="button" class="btn btn-is-primary btn-block">Primary</button>
                <button v-else type="button" class="btn btn-make-primary btn-block" 
                    @click="$emit('makePrimary', {'value':item, 'index':index})"><small>Set primary</small></button>
                </span>
                <input readonly :value="item.name" tabindex="-1" class="form-control read-only-white">
                <input readonly :value="item.url" tabindex="-1" class="form-control read-only-white">
                <button type="button" class="btn btn-delete-item" tabindex="-1" @click="$emit('remove', index)">&times;</button>
            </div>
        </draggable>
        <div v-if="isInvalid" class="invalid-feedback">
            {{ errorMessage }}
        </div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        "c-org-search": OrganizationSearch,
        draggable,
    },
})
export default class EditOrgList extends BaseControl {
    @Prop()
    public label: string;

    @Prop()
    public help: string;

    public customInput: boolean = false;
    public drag: boolean = false;
    public candidateItem: object = null;
    public customName: string = '';
    public customUrl: string = '';
    public localErrors = { name: '', url: '' };

    get isValidLocal() {
        return (this.localErrors.name || this.localErrors.url);
    }

    get localErrorMessage() {
        return `${this.localErrors.name}
                ${(this.localErrors.name && this.localErrors.url) ? ', ' : ''}
                ${this.localErrors.url}`;
    }

    public create() {
        this.$emit('create', this.candidateItem);
        this.candidateItem = null;
    }

    public createCustom() {
        if (this.validate()) {
            const customItem = {
                name: this.customName,
                url: this.customUrl,
                acronym: '',
                ror_id: '',
            };
            this.$emit('create', customItem);
            this.customName = null;
            this.customUrl = null;
        }
    }

    private validate() {
        let valid = true;
        if (!this.customName) {
            this.localErrors.name = 'Affiliation name is required';
            valid = false;
        }
        const schema = yup.object().shape({ url: yup.string().url().required() });
        if (!schema.isValidSync({ url: this.customUrl })) {
            console.log("its invalid");
            this.localErrors.url = 'Affiliation URL must be a valid URL';
            valid = false;
        }
        return valid;
    }
}
