import BaseControl from '@/components/forms/base';
import {Component, Prop} from 'vue-property-decorator';
import {markdownEditor as MarkdownEditor} from 'vue-simplemde';

enum ViewMode {
    code,
    view,
    code_and_view,
}

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}</label>
        </slot>
        <markdown-editor :value="value" @input="updateValue" ref="editor"></markdown-editor>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help" :help="help">
            <small style='margin-top: -30px;' class="form-text text-muted"><a href="https://en.wikipedia.org/wiki/Markdown" target="_blank">Markdown</a> styling is supported</small>
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        MarkdownEditor,
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
        return (this.$refs.editor as any).simplemde;
    }

    public mounted() {
        this.simplemde.codemirror.options.extraKeys.Tab = false;
        this.simplemde.codemirror.options.extraKeys['Shift-Tab'] = false;
    }
}

export default MarkDown;
