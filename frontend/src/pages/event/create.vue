<template>
    <form>
        <c-input type="text" v-model="state.content.title">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the event</small>
        </c-input>
        <c-input type="text" v-model="state.content.location">
            <label class="form-control-label" slot="label">Location</label>
            <small class="form-text text-muted" slot="help">The address of where the event takes place</small>
        </c-input>
        <markdown v-model="state.content.description" :errors="validationErrors.description">
            <label class="form-control-label" slot="label">Description</label>
            <small slot="help" class="form-text text-muted">Detailed information about the job</small>
        </markdown>
        <markdown v-model="state.content.summary">
            <label slot="label">Summary</label>
            <div slot="help">
                <button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    This field can be created from the description by pressing the summarize button.
                </small>
            </div>
        </markdown>
        <c-tagger v-model="state.content.tags.value" v-on:errors="setTagErrors">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>
</template>

<script lang="ts">
    import {basePageMixin} from 'components/base_page'
    import * as Vue from 'vue'
    import Component from 'vue-class-component'
    import  {CalendarEvent, Lens} from '../../store/common'
    import {api, createDefaultState, relatedCreateRecord, relatedTransformSuccess} from '../../api/index'
    import * as queryString from 'query-string'
    import {defaultEvent} from '../../store/defaults'
    import Markdown from 'components/forms/markdown.vue'
    import Tagger from 'components/tagger.vue'
    import Input from 'components/forms/input.vue'

    @Component({
        components: {
            // Multiselect,
            Markdown,
            'c-tagger': Tagger,
            'c-input': Input
        },
        computed: {
            'tags': function () {
                const self: any = this;
                return self.data.tags.map(t => {
                    return {name: t}
                });
            }
        },
        mixins: [basePageMixin]
    })
    class EventEditPage extends Vue {
        // determine whether you are creating or updating based on wat route you are on
        // update -> grab the appropriate state from the store
        // create -> use the default store state

        id = null;
        state = createDefaultState(defaultEvent);

        setTagErrors(tag_errors) {
            this.state.content.tags.errors = tag_errors;
        }

        matchUpdateUrl(pathname) {
            let match = pathname.match(/\/events\/([0-9]+)\/update\//);
            if (match !== null) {
                match = match[1];
            }
            return match
        }

        replaceFormState(id) {
            const self: any = this;
            if (id !== null) {
                self.retrieve('/events/' + id + '/');
            }
        }

        created() {
            this.id = this.matchUpdateUrl(document.location.pathname);
            this.replaceFormState(this.id);
        }

        createSummaryFromDescription() {
            relatedCreateRecord(
                    new Lens(this, ['state', 'content', 'summary']),
                    relatedTransformSuccess,
                    '/summarize/',
                    {description: this.state.content.description.value});
        }

        createOrUpdate() {
            const self: any = this;
            if (this.id === null) {
                self.create('/events/');
            } else {
                self.update('/events/' + this.id + '/');
            }

        }
    }

    export default EventEditPage;
</script>