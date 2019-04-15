import {Component, Prop} from 'vue-property-decorator'
import {Search} from 'components/search'
import Vue from 'vue'
import DatePicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Tagger from 'components/tagger'
import {EventAPI} from 'api'


@Component({
    // language=Vue
    template: `
        <c-search submitLabel="Submit an event" searchLabel="Search" submitUrl="/events/add/" :searchUrl="query">
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
                        <c-datepicker v-model="submissionDeadline" name="submissionDeadline" :clearButton="true">
                            <label class="form-control-label" slot="label">Submission Deadline</label>
                        </c-datepicker>
                        <c-datepicker v-model="startDate" name="startDate" :clearButton="true">
                            <label class="form-control-label" slot="label">Event Start Date</label>
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
export class SearchEvents extends Vue {
    private api = new EventAPI();
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
        return this.api.searchUrl(queryObject);
    }

    search() {
        window.location.href = this.query;
    }
}
