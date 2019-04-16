import {Component, Prop} from 'vue-property-decorator'
import {Search} from '@/components/search'
import Vue from 'vue'
import DatePicker from '@/components/forms/datepicker'
import Input from '@/components/forms/input'
import Tagger from '@/components/tagger'
import {CodebaseAPI} from "@/api";

const api = new CodebaseAPI();

@Component(<any>{
    // language=Vue
    template: `
        <c-search submitLabel="Archive a model" searchLabel="Search" submitUrl="/codebases/add/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <span @keyup.enter="search">
                            <c-input :required="false" label="Keywords" type="text" v-model="fullTextSearch" name="fullTextSearch" :errorMsgs="[]">
                            </c-input>
                        </span>
                        <c-datepicker v-model="startDate" :required="false" name="startDate" :errorMsgs="[]" :clearButton="true" label="Published After">
                        </c-datepicker>
                        <c-datepicker v-model="endDate" :required="false" name="endDate" :errorMsgs="[]" :clearButton="true" label="Published Before">
                        </c-datepicker>
                        <c-tagger v-model="tags" :required="false" placeholder="Type to add tags" label="Tags">
                        </c-tagger>
                    </div>
                </div>
            </div>
        </c-search>`,
    components: {
        'c-datepicker': DatePicker,
        'c-input': Input,
        'c-tagger': Tagger,
        'c-search': Search,
    }
})
export class SearchCodebases extends Vue {
    fullTextSearch: string = '';

    startDate: string | null = null;
    endDate: string | null = null;

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            published_after: this.startDate,
            published_before: this.endDate,
            tags: this.tags.map(tag => tag.name)
        };
        return api.searchUrl(queryObject);
    }

    search() {
        window.location.href = this.query;
    }
}
