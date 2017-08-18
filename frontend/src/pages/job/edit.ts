import * as Vue from 'vue'
import Component from 'vue-class-component'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import MessageDisplay from 'components/message_display'
import {api} from 'api/index'
import * as _ from 'lodash'
import {Job} from 'store/common'

@Component({
    template: `<form>
        <c-message-display :messages="serverErrors('non_field_errors')" :classNames="['alert', 'alert-danger']">
        </c-message-display>
        <c-input v-model="state.title" name="title" :server_errors="serverErrors('title')"
                    @clear="clearField">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the job</small>
        </c-input>
        <c-markdown v-model="state.description" name="description" :server_errors="serverErrors('description')"
                    @clear="clearField">
            <label class="form-control-label" slot="label">Description</label>
            <small slot="help" class="form-text text-muted">Detailed information about the job</small>
        </c-markdown>
        <c-markdown v-model="state.summary" name="summary" :server_errors="serverErrors('summary')" @clear="clearField">
            <label slot="label">Summary</label>
            <div slot="help">
                <button class="btn btn-secondary btn-sm" type="button" @click="createSummaryFromDescription">Summarize
                </button>
                <small class="form-text text-muted">A short summary of the job for display in search results.
                    This field can be created from the description by pressing the summarize button.
                </small>
            </div>
        </c-markdown>
        <c-tagger v-model="state.tags" name="tags" :server_errors="serverErrors('tags')" @clear="clearField">
        </c-tagger>
        <small class="form-text text-muted">A list of tags to associate with a job. Tags help people search for jobs.
        </small>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>`,
    components: {
        'c-markdown': Markdown,
        'c-tagger': Tagger,
        'c-input': Input,
        'c-message-display': MessageDisplay,
    }
})
class EditJob extends Vue {
    // determine whether you are creating or updating based on what route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    /*
        * FIXME: this shares many methods with the EditEvent component. Eventually those methods should be in a mixin
        * or a base class */

    state: Job = {
        description: '',
        summary: '',
        title: '',
        tags: []
    };

    matchUpdateUrl(pathname) {
        let match = pathname.match(/\/jobs\/([0-9]+)\/update\//);
        if (match !== null) {
            match = match[1];
        }
        return match
    }

    serverErrors(field_name: string) {
        let self: any = this;
        return self.errors.collect(field_name, 'server-side');
    }

    clearField(field_name: string) {
        let self: any = this;
        self.errors.remove(field_name, 'server-side');
        self.errors.remove('non_fields_errors', 'server-side');
    }

    initializeForm() {
        let id = this.matchUpdateUrl(document.location.pathname);
        if (id !== null) {
            this.retrieve(id);
        }
    }

    created() {
        this.initializeForm();
    }

    createSummaryFromDescription() {
        this.state.summary = _.truncate(this.state.description, {'length': 200, 'omission': '[...]'});
    }

    createOrUpdate() {
        if (this.state.id !== undefined) {
            this.update(this.state.id);
        } else {
            this.create();
        }

    }

    createMainServerError(err) {
        let self: any = this;
        self.errors.add('non_field_errors', err, 'server-side', 'server-side');
    }

    createServerErrors(err: any) {
        console.log({serverErrors: true, err});
        let self: any = this;
        for (const field_name in err) {
            self.errors.add(field_name, err[field_name], 'server-side', 'server-side');
        }
    }

    retrieve(id: number) {
        api.jobs.retrieve(id).then(state => this.state = state, this.createMainServerError);
    }

    create() {
        (this as any).errors.clear('server-side');
        api.jobs.create(this.state).then(drf_response => {
            switch (drf_response.kind) {
                case 'state':
                    this.state = drf_response.payload;
                    break;
                case 'validation_error':
                    this.createServerErrors(drf_response.payload);
                    break;
            }
        })
    }

    update(id: number) {
        (this as any).errors.clear('server-side');
        api.jobs.update(id, this.state).then(drf_response => {
            switch (drf_response.kind) {
                case 'state':
                    this.state = drf_response.payload;
                    break;
                case 'validation_error':
                    this.createServerErrors(drf_response.payload);
                    break;
            }
        })
    }
}

export default EditJob;