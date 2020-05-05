<template>
    <form>
        <c-input v-model="title" name="title" :errorMsgs="errors.title" label="Title" :required="config.title"
            help="A short title describing the job">
        </c-input>
        <c-markdown v-model="description" name="description" :errorMsgs="errors.description" label="Description"
            help="Detailed information about the job" :required="config.description">
        </c-markdown>
        <c-markdown v-model="summary" name="summary" :errorMsgs="errors.summary" label="Summary"
            :required="config.summary"
            help="A shorter summary of this job that will be displayed in search results. You can auto-create one from the description with the Auto-Summarize button.">
        </c-markdown>
        <button class="mt-n4 btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Auto-Summarize Description</button>
        <c-input v-model="external_url" name="external_url" :errorMsgs="errors.external_url" :required="config.external_url"
            label="External Job URL" help="URL for this job on an external website">
        </c-input>
        <c-date-picker v-model="application_deadline" name="application_deadline" :clearButton="true"
            :errorMsgs="errors.application_deadline" :required="false" label='Application deadline'>
        </c-date-picker>
        <c-tagger v-model="tags" name="tags" :errorsMsgs="errors.tags" :required="config.tags">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <c-message-display :messages="statusMessages">
        </c-message-display>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdateIfValid">Submit</button>
    </form>
</template>
<script lang="ts">
import Markdown from '@/components/forms/markdown';
import Tagger from '@/components/tagger';
import Input from '@/components/forms/input';
import MessageDisplay from '@/components/message_display';
import DatePicker from '@/components/forms/datepicker';
import {JobAPI} from '@/api/index';
import * as _ from 'lodash';
import * as yup from 'yup';
import {createFormValidator} from '@/pages/form';
import {Component, Prop} from 'vue-property-decorator';
import {HandlerWithRedirect} from '@/api/handler';

const api = new JobAPI();

export const schema = yup.object().shape({
    title: yup.string().required(),
    description: yup.string().required(),
    application_deadline: yup.date().min(new Date(), 'Please enter a valid date after today\'s date.').nullable(),
    summary: yup.string().required(),
    tags: yup.array().of(yup.object().shape({name: yup.string().required()})).min(0),
    external_url: yup.string().url('Please enter a valid URL').nullable(),
});

@Component({
    components: {
        'c-markdown': Markdown,
        'c-date-picker': DatePicker,
        'c-tagger': Tagger,
        'c-input': Input,
        'c-message-display': MessageDisplay,
    },
} as any)
class EditJob extends createFormValidator(schema) {
    // determine whether you are creating or updating based on what route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    @Prop()
    public _id: number | null;

    public detailPageUrl(state) {
        this.state.id = state.id;
        return api.detailUrl(this.state.id);
    }

    public initializeForm() {
        if (this._id !== null) {
            return this.retrieve(this._id);
        }
    }

    public created() {
        this.initializeForm();
    }

    public createSummaryFromDescription() {
        this.state.summary = _.truncate(this.state.description, {length: 500, omission: '[...]'});
    }

    public async createOrUpdateIfValid() {
        try {
            await this.validate();
            return this.createOrUpdate();
        } catch (e) {
            if (!(e instanceof yup.ValidationError)) {
                throw e;
            }
        }
    }

    public async createOrUpdate() {
        if (_.isNil(this.state.id)) {
            return api.create(new HandlerWithRedirect(this));
        } else {
            return api.update(this.state.id, new HandlerWithRedirect(this));
        }
    }

    public retrieve(id: number) {
        return api.retrieve(id).then((r) => {
            this.state = r.data;
            return r;
        });
    }
}

export default EditJob;

</script>
<style></style>
