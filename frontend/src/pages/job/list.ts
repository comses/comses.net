import {mapGetters} from 'vuex'
import JobItem from './item.vue'
import Paginator from '../../components/Paginator.vue'
import * as Vue from 'vue'
import Component from 'vue-class-component'
import router from '../../router-config'
import {api} from "../../store/index";

@Component({
    template: `
            <div>
                <form>
                    <div class="form-group">
                        <label for="jobSearch">Find a job</label>
                        <input type="text" class="form-control" id="jobSearch" placeholder="Search" :value="search"
                               @input="setSearch">
                    </div>
                    <router-link :to="{ name: 'job_list', query: { query: search, page: 1 }}" class="btn btn-primary">Search</router-link>
                </form>
                <div class="list-group">
                    <c-job-item
                        v-for="job in list.results"
                        v-bind:id="job.id"
                        v-bind:title="job.title"
                        v-bind:description="job.description"
                        v-bind:date_created="job.date_created">
                    </c-job-item>
                </div>
                <c-paginator
                        v-bind:n_pages="list.n_pages"
                        v-bind:page="list.page"
                        v-bind:route="'job_list'"
                        v-bind:query="list.query"
                        v-bind:on_click="search">
                </c-paginator>
            </div>`,
    computed: {
        ...mapGetters('jobs', ['list', 'search'])
    },
    components: {
        'c-job-item': JobItem,
        'c-paginator': Paginator
    }
})
class JobList extends Vue {

    setSearch(event) {
        this.$store.commit(api.job.mutations.setSearch(event.target.value));
    }
}

export default JobList;
