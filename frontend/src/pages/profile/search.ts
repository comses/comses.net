import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import * as Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import ProfileTagger from 'components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'
import {ProfileAPI} from 'api'


@Component({
    // language=Vue
    template: `
        <c-search submitLabel="Become a member" searchLabel="Search" submitUrl="/accounts/signup/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <c-input type="text" v-model="fullTextSearch" name="fullTextSearch">
                            <label class="form-control-label" slot="label">Full Text Search</label>
                        </c-input>
                        <c-tagger v-model="keywords" placeholder="Type to add tags" label="Tags">
                        </c-tagger>
                    </div>
                </div>
            </div>
        </c-search>`,
    components: {
        'c-date-picker': DatePicker,
        'c-input': Input,
        'c-tagger': ProfileTagger,
        'c-search': Search,
    }
})
export class SearchProfiles extends Vue {
    private api = new ProfileAPI();
    fullTextSearch: string = '';

    keywords: Array<{name: string}> = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            keywords: this.keywords.map(keyword => keyword.name)
        };
        return this.api.searchUrl(queryObject);
    }
}