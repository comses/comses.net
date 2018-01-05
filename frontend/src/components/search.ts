import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'

@Component({
    // language=Vue
    template: `
        <div>
            <a class="text-white" :href="submitUrl">
                <div class="btn btn-primary w-100">
                    {{ submitLabel }}
                </div>
            </a>
            <slot name="searchForm"></slot>
            <a class="text-white" :href="searchUrl">
                <div class="btn btn-primary w-100">
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