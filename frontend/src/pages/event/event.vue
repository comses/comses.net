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
            <c-tagger v-model="data.tags" v-on:errors="setTagErrors">
            </c-tagger>
            <button type="button" class="btn btn-primary" @click="createOrUpdate">Submit</button>
        </form>
    </div>
</template>

<script lang="ts">
    import * as Vue from 'vue'
    import Component from 'vue-class-component'
    import  {Job} from '../../store/common'
    import {api as axios} from '../../api/index'
    import * as queryString from 'query-string'
    import {job as defaultJob} from '../../store/defaults'
    import Markdown from 'components/markdown.vue'

    import Multiselect from 'vue-multiselect'
    // import {Errors} from 'store/common'
    import Tagger from 'components/tagger.vue'

    @Component({
        components: {
            // Multiselect,
            Markdown,
            'c-tagger': Tagger
        }
    })
    class JobCreate extends Vue {
        // determine whether you are creating or updating based on wat route you are on
        // update -> grab the appropriate state from the store
        // create -> use the default store state

        id = null;
        data = {...defaultJob};
        errors = { tags: []};
        isLoading = false;
        matchingTags = [];

        setTagErrors(tag_errors) {
            this.errors.tags = tag_errors;
        }

        matchUpdateUrl(pathname) {
            let match = pathname.match(/\/jobs\/([0-9]+)\/update\//);
            if (match !== null) {
                match = match[1];
            }
            return match
        }

        replaceFormState(id) {
            if (id !== null) {
                axios.get('/jobs/' + id + '/')
                        .then(response => {
                            console.log(response);
                            this.data = response.data;
                        })
            }
        }

        created() {
            this.id = this.matchUpdateUrl(document.location.pathname);
            this.replaceFormState(this.id);
        }

        createOrUpdate() {
            if (this.id === null) {
                axios.post('/jobs/', this.data)
                        .then(response => console.log(response))
                        .catch(response => this.errors = response.data);
            } else {
                axios.put('/jobs/' + this.id + '/', this.data)
                        .then(response => console.log(response))
                        .catch(response => this.errors = response.data);
            }
        }

        fetchMatchingTags(query) {
            this.isLoading = true;
            axios.get('/tags/?' + queryString.stringify({query, page: 1}))
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