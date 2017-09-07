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
        <c-search submitLabel="Create an event" searchLabel="Search" submitUrl="/events/add/" :searchUrl="query">
            <div slot="searchForm">
                <div class="card-metadata">
                    <div class="title">
                        Search
                    </div>
                    <div class="card-body">
                        <c-input type="text" v-model="fullTextSearch" name="fullTextSearch">
                            <label class="form-control-label" slot="label">Keywords</label>
                        </c-input>
                        <c-date-picker v-model="submissionDeadline" name="submissionDeadline" :clearButton="true">
                            <label class="form-control-label" slot="label">Submission Deadline</label>
                        </c-date-picker>
                        <c-date-picker v-model="startDate" name="startDate" :clearButton="true">
                            <label class="form-control-label" slot="label">Event Start Date</label>
                        </c-date-picker>
                        <c-input v-model="location" name="location" label="Location of Event">
                        </c-input>
                    </div>
                </div>
                <div class="card-metadata">
                    <div class="title">
                        Tags
                    </div>
                    <div class="card-body">
                        <c-tagger v-model="tags" placeholder="Type to add tags" label="Find Tags">
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
export class SearchEvents extends Vue {
    fullTextSearch: string = '';

    submissionDeadline = (new Date()).toISOString();
    startDate = (new Date()).toISOString();
    location: string = '';

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            start_date__gt: this.startDate,
            submission_deadline__th: this.submissionDeadline,
            location: this.location,
            tags: this.tags.map(tag => tag.name)
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