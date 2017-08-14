/* Need CSS module for this 

textarea {
  border: none;
  border-right: 1px solid #ccc;
  resize: none;
  outline: none;
  background-color: #f6f6f6;
  font-size: 14px;
  font-family: 'Monaco', courier, monospace;
  padding: 20px;
  height: 100%;
  width: 100%;
  overflow: auto;
}

code {
  color: #f66;
} */

import BaseControl from 'components/forms/base'
import {Component, Prop} from 'vue-property-decorator'
import * as marked from 'marked'

enum ViewMode {
    code,
    view,
    code_and_view
}

@Component({
    template: `<div class="form-group">
        <slot name="label"></slot>
        <div class="container-fluid p-0">
            <div class="btn-group">
                <button type="button" :class="[buttonStyle, {'active': displayView == viewMode.code }]"
                        @click="displayView = viewMode.code">
                    Edit
                </button>
                <button type="button" :class="[buttonStyle, {'active': displayView == viewMode.view }]"
                        @click="displayView = viewMode.view">
                    Preview
                </button>
                <button type="button" :class="[buttonStyle, {'active': displayView == viewMode.code_and_view }]"
                        @click="displayView = viewMode.code_and_view">
                    Side by Side
                </button>
            </div>
            <div class="row p-0 row-eq-height">
                <div :class="codeStyle">
                    <textarea :class="{'is-invalid': isInvalid }" :style="{ 'min-height': minHeight }" :value="value"
                                @input="updateValue($event.target.value)"
                                debounce="300">
                    </textarea>
                </div>
                <div :class="previewStyle">
                    <div v-html="markdown" class="preview"></div>
                </div>
            </div>
        </div>
        <div v-if="is-invalid" class="invalid-feedback">{{ errorMessage }}</div>
        <slot name="help"></slot>
    </div>`
})
class MarkDown extends BaseControl {
    @Prop({default: '10em'})
    minHeight: string;

    displayView: ViewMode = ViewMode.code_and_view;
    displayFullScreen: boolean = false;

    fullWidthClass = "p-1 col-12";
    halfWidthClass = "p-1 col-md-12 col-lg-6";
    hiddenClass = "hidden-xs-up";

    get viewMode() {
        return ViewMode;
    }

    get codeStyle() {
        switch (this.displayView) {
            case ViewMode.code:
                return this.fullWidthClass;
            case ViewMode.view:
                return this.hiddenClass;
            case ViewMode.code_and_view:
                return this.halfWidthClass;
        }
    }

    get previewStyle() {
        switch (this.displayView) {
            case ViewMode.code:
                return this.hiddenClass;
            case ViewMode.view:
                return this.fullWidthClass;
            case ViewMode.code_and_view:
                return this.halfWidthClass;
        }
    }

    get buttonStyle() {
        return 'btn btn-sm btn-secondary'
    }

    get markdown() {
        return marked.parse(this.value, {sanitize: true})
    }
}

export default MarkDown;