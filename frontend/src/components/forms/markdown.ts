import BaseControl from '@/components/forms/base';
import {Component, Prop} from 'vue-property-decorator';
import Vue from 'vue';
import VueSimplemde from 'vue-simplemde';
import 'simplemde/dist/simplemde.min.css';

Vue.component('vue-simplemde', VueSimplemde);


enum ViewMode {
    code,
    view,
    code_and_view,
}

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}
                <small class="ml-1 text-muted"><a href="https://en.wikipedia.org/wiki/Markdown" target="_blank">Markdown</a> styling is supported</small>
            </label>        
        </slot>
        <vue-simplemde :value="value" ref="markdownEditor"></vue-simplemde>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help" :help="help">
            <small class="mt-n4 form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        VueSimplemde
    },
})
class MarkDown extends BaseControl {
    @Prop({default: '10em'})
    public minHeight: string;

    @Prop()
    public label: string;

    @Prop()
    public help: string;

    get simplemde() {
        return (this.$refs.markdownEditor as any).simplemde;
    }

    public mounted() {
        this.simplemde.codemirror.options.extraKeys.Tab = false;
        this.simplemde.codemirror.options.extraKeys['Shift-Tab'] = false;
    }
}

export default MarkDown;
