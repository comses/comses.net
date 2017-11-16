import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import * as Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'
import {JobAPI} from 'api';


@Component({
    // language=Vue
    template: `
        <c-search submitLabel="Create an job" searchLabel="Search" submitUrl="/jobs/add/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <c-input type="text" v-model="fullTextSearch" name="fullTextSearch">
                            <label class="form-control-label" slot="label">Keywords</label>
                        </c-input>
                        <c-date-picker v-model="initialPostingDate" name="initialPostingDate" :clearButton="true">
                            <label class="form-control-label" slot="label">Initial Posting Date</label>
                        </c-date-picker>
                        <c-date-picker v-model="lastModifiedDate" name="lastModifiedDate" :clearButton="true">
                            <label class="form-control-label" slot="label">Last Modified Date</label>
                        </c-date-picker>
                        <c-tagger v-model="tags" placeholder="Type to add tags" label="Tags">
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
    lastModifiedDate = null;

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            date_created__gte: this.initialPostingDate,
            last_modified__gte: this.lastModifiedDate,
            tags: this.tags.map(tag => tag.name)
        };
        return this.api.searchUrl(queryObject);
    }
}
