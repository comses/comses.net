<template>
    <div>
        <h2 v-if>Edit a job</h2>
        <form>
            <div class="form-group">
                <label>Title</label>
                <input type="text" class="form-control" placeholder="Enter Title" v-model="data.title">
            </div>
            <div class="form-group">
                <label>Description</label>
                <markdown v-model="data.description"></markdown>
            </div>
            <multiselect
                    v-model="data.tags"
                    label="name"
                    track-by="name"
                    placeholder="Type to find keywords"
                    :options="matchingTags"
                    :multiple="true"
                    :loading="isLoading"
                    :searchable="true"
                    :internal-search="false"
                    :clear-on-select="false"
                    :close-on-select="false"
                    :options-limit="50"
                    :limit="6"
                    @search-change="fetchMatchingTags">
            </multiselect>
            <button type="button" class="btn btn-primary" @click="createOrUpdate">Submit</button>
        </form>
    </div>
</template>

<script lang="ts">
    import * as Vue from 'vue'
    import Component from 'vue-class-component'
    import {mapGetters, Store} from "vuex";
    import  {Job} from '../../store/common'
    import {api} from '../../store/index'
    import {api as axios} from '../../api/index'
    import * as queryString from 'query-string'
    import {job as defaultJob} from '../../store/defaults'
    import Markdown from 'components/markdown.vue'

    import Multiselect from 'vue-multiselect'
    import { Errors } from 'store/common'

    @Component({
        components: {
            Multiselect,
            Markdown
        }
    })
    class JobCreate extends Vue {
        // determine whether you are creating or updating based on wat route you are on
        // update -> grab the appropriate state from the store
        // create -> use the default store state

        data = {...defaultJob};
        errors: Errors<Job> = {};
        isLoading = false;
        matchingTags = [];

        routeId() {
            return parseInt(this.$route.params['jobId']);
        }

        replaceFormState() {
            const id = this.routeId();
            if (this.data.id !== id && !isNaN(id)) {
                axios.get('/api/wagtail/jobs/' + id + '/')
                        .then(response => {
                            console.log(response);
                            this.data = response.data;
                        })
            }
        }

        created() {
            this.replaceFormState();
        }

        createOrUpdate() {
            const id = this.routeId();
            let data = {...this.data};
            if (!isNaN(id)) {
                data.id = id;
            }
            const payload = api.job.actions.modify(data);
            this.$store.dispatch(payload)
                    .then(response => console.log(response))
                    .catch(response => this.errors = response.data);
        }

        fetchMatchingTags(query) {
            this.isLoading = true;
            axios.get('/api/wagtail/tags/?' + queryString.stringify({query, page: 1}))
                    .then(response => {
                        this.matchingTags = response.data.results;
                        this.isLoading = false;
                    })
                    .catch(response => {
                        this.isLoading = false;
                        this.errors = response.data
                    })
        }
    }

    export default JobCreate;
</script>