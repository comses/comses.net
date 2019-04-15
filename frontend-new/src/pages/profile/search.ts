import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import ProfileTagger from 'components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'
import {ProfileAPI} from 'api'


@Component(<any>{
    // language=Vue
    template: `
        <div>
            <a class="text-white" href="/accounts/signup/" v-if="!is_authenticated">
                <div class="btn btn-primary w-100" tabindex="0">
                    Become a member
                </div>
            </a>
            <div class="card-metadata">
                <h1 class="title">Search</h1>
                <div class="card-body">
                    <span @keyup.enter="search">
                        <c-input type="text" v-model="fullTextSearch" name="fullTextSearch" label="By Name" :required="false">
                        </c-input>
                    </span>
                    <c-tagger v-model="tags" :required="false" placeholder="Type to add tags" label="Keywords">
                    </c-tagger>
                </div>
            </div>
            <a class="text-white" :href="query">
                <div class="btn btn-primary w-100" tabindex="0">
                    Search
                </div>
            </a>
        </div>`,
    components: {
        'c-date-picker': DatePicker,
        'c-input': Input,
        'c-tagger': ProfileTagger,
        'c-search': Search,
    }
})
export class SearchProfiles extends Vue {
    @Prop()
    is_authenticated: boolean;

    private api = new ProfileAPI();
    fullTextSearch: string = '';

    tags: Array<{name: string}> = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            tags: this.tags.map(keyword => keyword.name),
            page: 1,
        };
        return this.api.searchUrl(queryObject);
    }

    search() {
        window.location.href = this.query;
    }
}
