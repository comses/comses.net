import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import * as Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import {CodebaseAPI} from 'api';


@Component({
    // language=Vue
    template: `
        <c-search submitLabel="Archive a model" searchLabel="Search" submitUrl="/codebases/add/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <c-input type="text" v-model="fullTextSearch" name="fullTextSearch" :errorMsgs="[]">
                            <label class="form-control-label" slot="label">Keywords</label>
                        </c-input>
                        <c-date-picker v-model="startDate" name="startDate" :errorMsgs="[]" :clearButton="true">
                            <label class="form-control-label" slot="label">Published Start Date</label>
                        </c-date-picker>
                        <c-date-picker v-model="endDate" name="endDate" :errorMsgs="[]" :clearButton="true">
                            <label class="form-control-label" slot="label">Published End Date</label>
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
export class SearchCodebases extends Vue {
    private api = new CodebaseAPI();
    fullTextSearch: string = '';

    startDate: string | null = null;
    endDate: string | null = null;

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            start_date: this.startDate,
            end_date: this.endDate,
            tags: this.tags.map(tag => tag.name)
        };
        return this.api.searchUrl(queryObject);
    }
}
