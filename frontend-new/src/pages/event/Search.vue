<template>
    <c-search submitLabel="Submit an event" searchLabel="Search" submitUrl="/events/add/" :searchUrl="query">
        <div slot="searchForm">
            <div class="card-metadata">
                <div class="title">
                    Search
                </div>
                <div class="card-body">
                        <span @keyup.enter="search">
                            <c-input type="text" v-model="fullTextSearch" name="fullTextSearch" label="Keywords"
                                     :required="false">
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
    </c-search>
</template>

<script lang="ts">
    import {Component, Prop} from 'vue-property-decorator';
    import {Search} from '@/components/search';
    import DatePicker from '@/components/forms/DatePicker.vue';
    import Input from '@/components/forms/input';
    import Tagger from '@/components/tagger';
    import {EventAPI} from '@/api';


    @Component({
        // language=Vue
        components: {
            'c-datepicker': DatePicker,
            'c-input': Input,
            'c-tagger': Tagger,
            'c-search': Search,
        },
    })
    export class SearchEvents extends Vue {

        get query() {
            const queryObject = {
                query: this.fullTextSearch,
                start_date__gte: this.startDate,
                submission_deadline__gte: this.submissionDeadline,
                tags: this.tags.map((tag) => tag.name),
            };
            return this.api.searchUrl(queryObject);
        }

        public fullTextSearch: string = '';
        public submissionDeadline = null;
        public startDate = null;
        public tags: Array<{name: string}> = [];
        public contributors = [];
        private api = new EventAPI();

        public search() {
            window.location.href = this.query;
        }
    }

</script>

<style scoped>

</style>