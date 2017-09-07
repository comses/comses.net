import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import * as Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'


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
                            <label class="form-control-label" slot="label">Universal Search</label>
                        </c-input>
                    </div>
                </div>
                <div class="card-metadata">
                    <div class="title">
                        Tags
                    </div>
                    <div class="card-body">
                        <c-tagger v-model="keywords" placeholder="Type to add tags" label="Find Keywords">
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
export class SearchProfiles extends Vue {
    fullTextSearch: string = '';

    keywords: Array<{name: string}> = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            keywords: this.keywords.map(keyword => keyword.name)
        };
        Object.keys(queryObject).forEach(key => {
           if (_.isEmpty(queryObject[key]) || _.isNull(queryObject[key])) {
               delete queryObject[key];
           }
        });
        const qs = queryString.stringify(queryObject);
        return `/search/${ qs ? `?${qs}`: ''}`;
    }
}