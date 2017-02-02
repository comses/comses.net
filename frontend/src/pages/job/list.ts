import {mapGetters} from 'vuex'
import JobItem from './item.vue'
import Paginator from '../../components/Paginator.vue'
import * as Vue from 'vue'
import Component from 'vue-class-component'
import router from '../../router-config'
import {api} from "../../store/index";

@Component({
    template: `
            <div class="container">
                <div class="form-group row">
                    <div class="col-xs-12 col-sm-9">
                        <input type="text" class="form-control" id="jobSearch" placeholder="Search" :value="search"
                           @input="setSearch">     
                    </div>
                    <div class="col-sm-3">
                        <router-link :to="{ name: 'job_list', query: { query: search, page: 1 }}" class="btn btn-primary">Search</router-link>
                        <router-link :to="{ name: 'job_update', params: { jobId: 1 }}" class="btn btn-primary btn float-md-right mt-xs-1">
                            <span class="fa fa-plus"></span>    
                        </router-link>
                    </div>
                </div>
                <div class="list-group row">
                    <c-job-item
                        v-for="job in list.results"
                        v-bind:id="job.id"
                        v-bind:title="job.title"
                        v-bind:description="job.description"
                        v-bind:date_created="job.date_created"
                        v-bind:detail_page="'job_detail'"
                        v-bind:update_page="'job_update'">
                    </c-job-item>
                </div>
                <div class="row pt-3">
                    <c-paginator
                            v-bind:n_pages="list.n_pages"
                            v-bind:page="list.page"
                            v-bind:route="'job_list'"
                            v-bind:query="list.query"
                            v-bind:on_click="search">
                    </c-paginator>                
                </div>
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
