import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import * as Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import * as queryString from 'query-string'
import * as _ from 'lodash'
import {eventAPI} from 'api'


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

    submissionDeadline = null;
    startDate = null;

    tags: Array<{name: string}> = [];
    contributors = [];

    get query() {
        const queryObject = {
            query: this.fullTextSearch,
            start_date__gte: this.startDate,
            submission_deadline__gte: this.submissionDeadline,
            tags: this.tags.map(tag => tag.name)
        };
        Object.keys(queryObject).forEach(key => {
           if (_.isEmpty(queryObject[key]) || _.isNull(queryObject[key])) {
               delete queryObject[key];
           }
        });
        const qs = queryString.stringify(queryObject);
        return `${eventAPI.baseUrl}${ qs ? `?${qs}`: ''}`;
    }
}