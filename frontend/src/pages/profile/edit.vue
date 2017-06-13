<template>
    <form>
        <c-message-display :messages="serverErrors('non_field_errors')" :classNames="['alert', 'alert-danger']">
        </c-message-display>
        <c-input v-model="state.given_name" name="given_name" :server_errors="serverErrors('given_name')" @clear="clearField">
            <label class="form-control-label" slot="label">Given Name</label>
        </c-input>
        <c-input v-model="state.family_name" name="family_name" :server_errors="serverErrors('family_name')" @clear="clearField">
            <label class="form-control-label" slot="label">Family Name</label>
        </c-input>
        <c-textarea v-model="state.research_interests" name="research_interests" :server_errors="serverErrors('research_interests')" @clear="clearField">
            <label class="form-control-label" slot="label">Research Interests</label>
            <small class="form-text text-muted" slot="help"></small>
        </c-textarea>
        <label class="form-control-label">Profile Picture Upload</label>
        <dropzone id="imageUpload" acceptedFileTypes="image/*" :url="uploadImageURL" :headers="{'X-CSRFToken': csrftoken }" ref="picture_upload" :useFontAwesome="true">
        </dropzone>
        <div class="form-group">
            <div class="form-control-label">{{ state.avatar }}</div>
        </div>
        <c-input type="url" v-model="state.orcid" name="orcid" :server_errors="serverErrors('orcid')" @clear="clearField">
            <label class="form-control-label" slot="label">ORCID</label>
            <small class="form-text text-muted" slot="help">Your ORCID</small>
        </c-input>
        <c-input type="url" v-model="state.personal_url" name="personal_url" :server_errors="serverErrors('personal_url')" @clear="clearField">
            <label class="form-control-label" slot="label">Personal URL</label>
            <small class="form-text text-muted" slot="help">A link to your personal modeling related website</small>
        </c-input>
        <c-input type="url" v-model="state.professional_url" name="professional_url" :server_errors="serverErrors('professional_url')" @clear="clearField">
            <label class="form-control-label" slot="label">Professional URL</label>
            <small class="form-text text-muted" slot="help">A link to your profile at the your place of work</small>
        </c-input>
        <c-input v-model="state.institution_name" name="institution_name" :server_errors="serverErrors('institution_name')" @clear="clearField">
            <label class="form-control-label" slot="label">Institution</label>
            <small class="form-text text-muted" slot="help">The primary place you are currently working at</small>
        </c-input>
        <c-input v-model="state.institution_url" name="institution_url" :server_errors="serverErrors('institution_url')" @clear="clearField">
            <label class="form-control-label" slot="label">Institution URL</label>
        </c-input>
        <c-textarea v-model="state.bio" name="bio" :server_errors="serverErrors('bio')" @clear="clearField">
            <label class="form-control-label" slot="label">Biography</label>
        </c-textarea>
        <c-edit-degrees :value="state.degrees" @create="state.degrees.push($event)" @remove="state.degrees.splice($event, 1)" @modify="state.degrees.splice($event.index, 1, $event.value)" name="degrees" :server_errors="serverErrors('degrees')" @clear="clearField">
            <label class="form-control-label" slot="label">Degrees</label>
            <small class="form-text text-muted" slot="help">The institution and name of the degrees you recieved</small>
        </c-edit-degrees>
        <c-tagger v-model="state.keywords" name="keywords" :server_errors="serverErrors('keywords')" @clear="clearField">
        </c-tagger>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>
</template>
<script lang="ts">
import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import Markdown from 'components/forms/markdown.vue'
import Tagger from 'components/tagger.vue'
import Input from 'components/forms/input.vue'
import Datepicker from 'components/forms/datepicker.vue';
import TextArea from 'components/forms/textarea.vue'
import MessageDisplay from 'components/message_display.vue'
import EditItems from 'components/edit_items.vue'
import { api, getCookie } from 'api/index'
import { MemberProfile } from 'store/common'
import * as _ from 'lodash'
import * as Dropzone from 'vue2-dropzone'

@Component({
    components: {
        'c-markdown': Markdown,
        'c-message-display': MessageDisplay,
        'c-datepicker': Datepicker,
        'c-tagger': Tagger,
        'c-textarea': TextArea,
        'c-input': Input,
        'c-edit-degrees': EditItems,
        'dropzone': Dropzone,
    }
})
export default class EditProfile extends Vue {
    state: MemberProfile = {
        date_joined: '2006-01-01',
        given_name: '',
        family_name: '',
        username: '',

        follower_count: 0,
        following_count: 0,

        codebases: [],

        bio: '',
        degrees: [],
        full_member: false,
        institution_name: '',
        institution_url: '',
        keywords: [],
        orcid: '',
        orcid_url: '',
        personal_url: '',
        picture: '',
        professional_url: '',
        profile_url: '',
        research_interests: ''
    };

    get csrftoken() {
        // console.log(getCookie('csrftoken'));
        return getCookie('csrftoken');
    }

    serverErrors(field_name: string) {
        let self: any = this;
        return self.errors.collect(field_name, 'server-side');
    }

    clearField(field_name: string) {
        let self: any = this;
        self.errors.remove(field_name, 'server-side');
    }

    matchUpdateUrl(pathname: string): string | null {
        let match = pathname.match(/\/users\/([0-9a-z\_\-]+)\/update\//);
        if (match !== null) {
            return match[1];
        }
        return match
    }

    createMainServerError(err) {
        let self: any = this;
        self.errors.add('non_field_errors', err, 'server-side', 'server-side');
    }

    createServerErrors(err: any) {
        let self: any = this;
        if (err.hasOwnProperty('non_field_errors')) {
            this.createMainServerError((<any>err).non_field_errors);
            delete err.non_field_errors;
        }
        for (const field_name in err) {
            self.errors.add(field_name, err[field_name], 'server-side', 'server-side');
        }
    }

    created() {
        let username = this.matchUpdateUrl(window.location.href);
        if (username !== null) {
            this.retrieve(username)
        }
    }

    createOrUpdate() {
        if (this.state.username === undefined) {
            this.create();
        } else {
            this.update(this.state.username);
        }
    }

    retrieve(username: string) {
        return api.users.retrieve(username).then(state => this.state = state);
    }

    get uploadImageURL() {
        return `${window.location.href}picture/`;
    }

    create() {
        (this as any).errors.clear('server-side');
        return api.users.create(this.state).then(drf_response => {
            (this as any).errors.clear('server-side');
            switch (drf_response.kind) {
                case 'state':
                    this.state = drf_response.payload;
                    break;
                case 'validation_error':
                    this.createServerErrors(drf_response.payload);
                    break;
            }
        });
    }

    update(username: string) {
        (this as any).errors.clear('server-side');
        return api.users.update(username, this.state).then(drf_response => {
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
</script>
