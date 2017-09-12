import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import Datepicker from 'components/forms/datepicker';
import TextArea from 'components/forms/textarea'
import MessageDisplay from 'components/message_display'
import EditItems from 'components/edit_items'
import {profileAPI} from 'api'
import * as _ from 'lodash'
import * as Dropzone from 'vue2-dropzone'
import {createFormValidator} from 'pages/form'
import {HandlerWithRedirect} from "api/handler";
import * as yup from 'yup'

export const schema = yup.object().shape({
    given_name: yup.string().required(),
    family_name: yup.string().required(),
    research_interests: yup.string(),
    orcid: yup.string(),
    personal_url: yup.string().url(),
    professional_url: yup.string().url(),
    institution_name: yup.string(),
    institution_url: yup.string().url(),
    bio: yup.string(),
    degrees: yup.array().of(yup.string().required()),
    keywords: yup.array().of(yup.object().shape({name: yup.string().required()}))
});

@Component(<any>{
    template: `<form>
        <c-input v-model="given_name" name="given_name" :errorMsgs="errors.given_name" label="Given Name">
        </c-input>
        <c-input v-model="family_name" name="family_name" :errorMsgs="errors.family_name" label="Family Name">
        </c-input>
        <c-textarea v-model="research_interests" name="research_interests" :errorMsgs="errors.research_interests" label="Research Interests">
        </c-textarea>
        <div class="form-group">
            <label class="form-control-label">Profile Picture Upload</label>
            <input type="file" class="form-control-file" @change="uploadImage">
            <img v-if="avatar" :src="avatar">
        </div>
        </dropzone>
        <c-input type="url" v-model="orcid" name="orcid" :errorMsgs="errors.orcid" label="ORCID" help="Your ORCID">
        </c-input>
        <c-input type="url" v-model="personal_url" name="personal_url" :errorMsgs="errors.personal_url" label="Personal URL" help="A link to your personal modeling related website">
        </c-input>
        <c-input type="url" v-model="professional_url" name="professional_url" :errorMsgs="errors.professional_url" 
                 label="Professional URL" help="A link to your profile at the your place of work">
        </c-input>
        <c-input v-model="institution_name" name="institution_name" :errorMsgs="errors.institution_name"
            label="Institution" help="The primary place you are currently working at">
        </c-input>
        <c-input v-model="institution_url" name="institution_url" :errorMsgs="errors.institution_url" label="Institution URL">
        </c-input>
        <c-textarea v-model="bio" name="bio" :errorMsgs="errors.bio" label="Biography">
        </c-textarea>
        <c-edit-degrees :value="degrees" @create="degrees.push($event)" @remove="degrees.splice($event, 1)" @modify="degrees.splice($event.index, 1, $event.value)" name="degrees" :errorMsgs="errors.degrees">
            <label class="form-control-label" slot="label">Degrees</label>
            <small class="form-text text-muted" slot="help">The institution and name of the degrees you recieved</small>
        </c-edit-degrees>
        <c-tagger v-model="keywords" name="keywords" :errorMsgs="errors.keywords" label="Keywords">
        </c-tagger>
        <c-message-display :messages="statusMessages">
        </c-message-display>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Submit</button>
    </form>`,
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
export default class EditProfile extends createFormValidator(schema) {
    @Prop
    _username: string | null;

    detailPageUrl(state) {
        this.state.username = state.username;
        return profileAPI.detailUrl(this.state.username);
    }

    detailUrlParams(state) {
        return state.username;
    }

    initializeForm() {
        if (this._username !== null) {
            return this.retrieve(this._username)
        }
    }

    created() {
        this.initializeForm();
    }

    createOrUpdate() {
        return profileAPI.update(this.state.username, new HandlerWithRedirect(this));
    }

    retrieve(username: string) {
        return profileAPI.retrieve(username).then(r => this.state = r.data);
    }

    async uploadImage(event) {
        const file = event.target.files[0];
        const response = await profileAPI.uploadProfilePicture({username: this.state.username}, file);
        this.state.avatar = response.data;
    }

    get uploadImageURL() {
        return `${window.location.href}picture/`;
    }
}