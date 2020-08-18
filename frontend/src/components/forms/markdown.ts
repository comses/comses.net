import BaseControl from '@/components/forms/base';
import { Component, Prop } from 'vue-property-decorator';
import Vue from 'vue';
import VueSimplemde from 'vue-simplemde';
import 'simplemde/dist/simplemde.min.css';

Vue.component('vue-simplemde', VueSimplemde);

@Component({
  template: `<div :class="['form-group', {'child-is-invalid': isInvalid }]">
        <slot name="label" :label="label">
            <label :class="['form-control-label', requiredClass]">{{ label }}
                <small class="ml-1 text-muted"><a href="https://en.wikipedia.org/wiki/Markdown" target="_blank">Markdown</a> styling is supported</small>
            </label>
        </slot>
        <vue-simplemde @input="emitValue" :configs="configs" :value="value" ref="markdownEditor"></vue-simplemde>
        <div v-if="isInvalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help" :help="help">
        </slot>
    </div>`,
  components: {
    VueSimplemde,
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

  public emitValue(value) {
    this.$emit('input', value);
  }

  public refresh() {
    this.simplemde.codemirror.refresh();
  }

  get simplemde() {
    return (this.$refs.markdownEditor as any).simplemde;
  }

  public mounted() {
    const self = this;
    const codemirror = this.simplemde.codemirror;
    codemirror.options.extraKeys.Tab = false;
    codemirror.options.extraKeys['Shift-Tab'] = false;
  }
}
