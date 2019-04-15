import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'

// Tabbing is not consistent between browsers but tabbing order works as expected in
// in Chrome, Firefox and Safari. If tabindex is placed on <a> then tabbing would not
// work for Firefox or Safari. Pressing enter on search or submit when focused does
// not work in Safari.
//
// See https://www.alexlande.com/articles/cross-browser-tabindex-woes/ for details
@Component({
    // language=Vue
    template: `
        <div>
            <a class="text-white" :href="submitUrl">
                <div class="btn btn-primary w-100" tabindex="0">
                    {{ submitLabel }}
                </div>
            </a>
            <slot name="searchForm"></slot>
            <a class="text-white" :href="searchUrl">
                <div class="btn btn-primary w-100" tabindex="0">
                    {{ searchLabel }}
                </div>
            </a>
        </div>`
})
export class Search extends Vue {
    @Prop()
    submitLabel: string;

    @Prop()
    submitUrl: string;

    @Prop()
    searchLabel: string;

    @Prop()
    searchUrl: string;
}
