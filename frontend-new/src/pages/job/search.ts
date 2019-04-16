import {Component, Prop} from 'vue-property-decorator'
import {Search} from '@/components/search'
import Vue from 'vue'
import DatePicker from '@/components/forms/datepicker'
import Input from '@/components/forms/input'
import Tagger from '@/components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'
import {JobAPI} from "@/api";


@Component({
    // language=Vue
    template: `
        <c-search submitLabel="Post a job" searchLabel="Search" submitUrl="/jobs/add/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <span @keyup.enter="search">
                            <c-input type="text" v-model="fullTextSearch" name="fullTextSearch" label="Keywords" :required="false">
                            </c-input>
                        </span>
                        <c-date-picker v-model="initialPostingDate" name="initialPostingDate" :clearButton="true"
                            :required="false" label='Initial post date'>
                        </c-date-picker>
                        <c-date-picker v-model="applicationDeadline" name="applicationDeadline" :clearButton="true"
                            :required="false" label='Application deadline'>
                        </c-date-picker>
                        <c-tagger v-model="tags" :required="false" placeholder="Type to add tags" label="Tags">
                        </c-tagger>
                    </div>
                </div>
            </div>
        </c-search>`,
    components: {
        'c-date-picker': DatePicker,
        'c-input': Input,
        'c-tagger': Tagger,
        'c-search': Search,
    }
})
export class SearchJobs extends Vue {
    readonly api = new JobAPI();
    fullTextSearch: string = '';

    initialPostingDate = null;
    applicationDeadline = null;

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            date_created__gte: this.initialPostingDate,
            application_deadline__gte: this.applicationDeadline,
            tags: this.tags.map(tag => tag.name)
        };
        return this.api.searchUrl(queryObject);
    }

    search() {
        window.location.href = this.query;
    }
}
