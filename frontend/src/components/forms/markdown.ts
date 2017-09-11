import BaseControl from 'components/forms/base'
import {Component, Prop} from 'vue-property-decorator'
import {markdownEditor as MarkdownEditor} from 'vue-simplemde'

enum ViewMode {
    code,
    view,
    code_and_view
}

@Component({
    template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label class="form-control-label">{{ label }}</label>
        </slot>
        <markdown-editor :value="value" @input="updateValue"></markdown-editor>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help" :help="help">
            <small class="form-text text-muted">{{ help }}</small>
        </slot>
    </div>`,
    components: {
        MarkdownEditor
    }
})
class MarkDown extends BaseControl {
    @Prop({default: '10em'})
    minHeight: string;

    @Prop()
    label: string;

    @Prop()
    help: string;
}

export default MarkDown;