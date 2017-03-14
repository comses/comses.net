<template>
    <form>
        <div class="form-group">
            <label>Title</label>
            <input type="text" class="form-control" placeholder="Enter Title" v-model="data.title">
        </div>
        <div class="form-group">
            <label>Description</label>
            <markdown v-model="data.description"></markdown>
            <small class="form-text text-muted">Detailed information about the job</small>
        </div>
        <div class="form-group">
            <label>Summary</label>
            <markdown class="form-control" v-model="data.summary"></markdown>
            <button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Summarize</button>
            <small class="form-text text-muted">A short summary of the job for display in search results.
                This field can be created from the description by pressing the summarize button.
            </small>
        </div>
        <c-tagger v-model="tags" v-on:errors="setTagErrors">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>
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
        },
        computed: {
            'tags': function() {
                const self: any = this;
                return self.data.tags.map(t => { return {name: t}});
            }
        }
    })
    class JobCreate extends Vue {
        // determine whether you are creating or updating based on wat route you are on
        // update -> grab the appropriate state from the store
        // create -> use the default store state

        id = null;
        data = {...defaultJob};
        errors: any = {tags: []};
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

        createSummaryFromDescription() {
            axios.post('/summarize/', {description: <any>this.data.description})
                .then(response => this.data.summary = response.data)
                .catch(response => this.errors.summary = response.data);
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
    }

    export default JobCreate;
</script>