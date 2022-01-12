import BaseControl from '@/components/forms/base';
import { Component, Prop } from 'vue-property-decorator';
import Vue from 'vue';
import VueEasymde from 'vue-easymde';
import 'easymde/dist/easymde.min.css';

@Component({
  template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}
                <small class="ml-1 text-muted"><a href="https://en.wikipedia.org/wiki/Markdown" target="_blank">Markdown</a> styling is supported</small>
            </label>
        </slot>
        <vue-easymde @input="handleInput" :configs="configs" :value="value" ref="markdownEditor"></vue-easymde>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help" :help="help">
        </slot>
    </div>`,
  components: {
    'vue-easymde': VueEasymde,
  },
})
export default class Markdown extends BaseControl {
  @Prop()
  public label: string;

  @Prop()
  public help: string;

  @Prop()
  public value: string;

  get configs() {
    return {
      placeholder: this.help,
      toolbar: [
        'bold', 'italic', 'heading', '|',
        'code', 'quote', 'unordered-list', 'ordered-list', '|',
        'horizontal-rule', 'link', 'image', 'table', '|',
        'preview', 'side-by-side', 'fullscreen', '|',
        'guide',
      ],
    };
  }

  get easymde() {
    return (this.$refs.markdownEditor as any).easymde;
  }

  public refresh() {
    this.easymde.codemirror.refresh();
  }

  handleInput(value) {
    console.log("emitting input value: ", value);
    this.$emit('input', value);
  }

  mounted() {
    const codemirror = this.easymde.codemirror;
    codemirror.options.extraKeys.Tab = false;
    codemirror.options.extraKeys['Shift-Tab'] = false;
  }



}
