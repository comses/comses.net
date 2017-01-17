import {mapGetters, mapMutations} from 'vuex'
import JobItem from './JobItem.vue'
import Paginator from './Paginator.vue'
import * as Vue from 'vue'
import Component from 'vue-class-component'
import router from '../router-config'
import { Actions } from '../store/types'
import {SET_JOB_QUERY_TEXT} from '../store/types'

@Component({
    template: `
            <div>
                <form>
                    <div class="form-group">
                        <label for="jobSearch">Find a job</label>
                        <input type="text" class="form-control" id="jobSearch" placeholder="Search" :value="job_query"
                               @input="set_query">
                    </div>
                    <router-link :to="{ name: 'job_list', query: { query, page_ind: 1 }}">Search</router-link>
                </form>
                <c-job-item
                        v-for="job in jobs"
                        v-bind:id="job.id"
                        v-bind:title="job.title"
                        v-bind:description="job.description"
                        v-bind:date_created="job.date_created">
                </c-job-item>
                <c-paginator
                        v-bind:n_pages="pagination.n_pages"
                        v-bind:page_ind="pagination.page_ind"
                        v-bind:route="'job_list'"
                        v-bind:query="pagination.query"
                        v-bind:on_click="query">
                </c-paginator>
            </div>`,
    computed: {
        ...mapGetters(['jobs', 'pagination', 'job_query'])
    },
    methods: {
        ...mapMutations([SET_JOB_QUERY_TEXT])
    },
    components: {
        'c-job-item': JobItem,
        'c-paginator': Paginator
    }
})
class JobList extends Vue {
    get query() {
        return this.$store.getters.job_query;
    }

    set_query(event) {
        this.$store.commit(SET_JOB_QUERY_TEXT, event.target.value);
    }
}

export default JobList;
