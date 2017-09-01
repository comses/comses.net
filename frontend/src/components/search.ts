import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import * as _ from 'lodash'

@Component({
    // language=Vue
    template: `<div>
        <div class="btn btn-primary w-100">
            <a class="text-white" :href="submitUrl">{{ submitLabel }}</a>
        </div>
        <slot name="searchForm"></slot>
        <div class="btn btn-primary w-100">
            <a class="text-white" :href="searchUrl">{{ searchLabel }}</a>
        </div>
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