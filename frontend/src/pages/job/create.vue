<template>
    <div>
        <h2>Create a new job</h2>
        <form>
            <div class="form-group">
                <label>Title</label>
                <input type="text" class="form-control" placeholder="Enter Title" v-model="title">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea class="form-control" v-model="description"></textarea>
            </div>
            <multiselect
                    v-model="selectedTags"
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
            <button type="button" class="btn btn-primary" @click="create">Submit</button>
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

    import Multiselect from 'vue-multiselect'

    @Component({
        components: {
            Multiselect
        }
    })
    class JobCreate extends Vue implements Job {
        // determine whether you are creating or updating based on wat route you are on
        // update -> grab the appropriate state from the store
        // create -> use the default store state

        error = '';
        description = '';
        isLoading = false;
        selectedTags = [];
        matchingTags = [];
        title = '';

        create() {
            this.$store.dispatch(api.job.actions.modify({
                description: this.description,
                title: this.title,
                tags: this.selectedTags
            }))
                    .then(repsonse => this.$router.go(-1))
                    .catch(response => this.error = response.data);
        }

        fetchMatchingTags(query) {
            this.isLoading = true;
            axios.get('/api/wagtail/tag/?' + queryString.stringify({ query, page: 1 }))
                    .then(response => {
                        this.matchingTags = response.data.results
                        this.isLoading = false;
                    })
                    .catch(response => {
                        this.isLoading = false;
                        this.error = response.data
                    })
        }
    }

    export default JobCreate;
</script>