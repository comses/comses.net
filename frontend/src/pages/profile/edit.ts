import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import Markdown from 'components/forms/markdown'
import Tagger from 'components/tagger'
import Input from 'components/forms/input'
import Datepicker from 'components/forms/datepicker';
import TextArea from 'components/forms/textarea'
import MessageDisplay from 'components/message_display'
import EditItems from 'components/edit_items'
import {ProfileAPI} from 'api'
import * as _ from 'lodash'
import * as Dropzone from 'vue2-dropzone'
import {createFormValidator} from 'pages/form'
import {HandlerWithRedirect} from "api/handler";
import * as yup from 'yup'

export const schema = yup.object().shape({
    given_name: yup.string().required(),
    family_name: yup.string().required(),
    research_interests: yup.string(),
    orcid_url: yup.string(),
    personal_url: yup.string().url(),
    professional_url: yup.string().url(),
    institution_name: yup.string(),
    institution_url: yup.string().url(),
    bio: yup.string(),
    degrees: yup.array().of(yup.string().required()),
    keywords: yup.array().of(yup.object().shape({name: yup.string().required()}))
});

@Component(<any>{
    template: `<form v-cloak>
        <div class="form-group">
            <label class="form-control-label">Profile Picture</label>
            <input type="file" class="form-control-file" @change="uploadImage">
            <img class='mt-3 d-block rounded-circle img-fluid img-thumbnail' alt='Profile Image' v-if="state.avatar" :src="state.avatar">
            <img class='mt-3 d-block rounded-circle img-fluid img-thumbnail' src='holder.js/150x150' v-else>
        </div>

        <div class='form-group' v-if='orcid_url'>
            ORCID 
            <a target='_blank' href='https://orcid.org/'><span class='ai ai-orcid'></span></a> | 
            <a target='_blank' :href='orcid_url'>{{ orcid_url }}</a>
        </div>
        <div class='form-group' v-else>
            <span class='fa fa-link'></span> <a title='orcid' href='/accounts/orcid/login/?process=connect'>Connect your ORCID account</a>
            <span class='ai ai-orcid'></span>
        </div>

        <c-input v-model="given_name" name="given_name" :errorMsgs="errors.given_name" label="Given Name" 
            :required="config.given_name">
        </c-input>
        <c-input v-model="family_name" name="family_name" :errorMsgs="errors.family_name" label="Family Name" 
            :required="config.family_name">
        </c-input>
        <c-markdown v-model="bio" name="bio" :errorMsgs="errors.bio" label="Bio" :required="config.bio">
        </c-markdown>
        <c-markdown v-model="research_interests" name="research_interests" :errorMsgs="errors.research_interests" 
            label="Research Interests" :required="config.research_interests">
        </c-markdown>

        <c-input type="url" v-model="personal_url" name="personal_url" :errorMsgs="errors.personal_url" 
            label="Personal URL" help="A link to your personal modeling related website" :required="config.personal_url">
        </c-input>
        <c-input type="url" v-model="professional_url" name="professional_url" :errorMsgs="errors.professional_url" 
                 label="Professional URL" help="A link to your institutional or professional profile page."
                 :required="config.professional_url">
        </c-input>
        <c-input v-model="institution_name" name="institution_name" :errorMsgs="errors.institution_name"
            label="Institution" help="The primary place you are currently working at" 
            :required="config.institution_name">
        </c-input>
        <c-input v-model="institution_url" name="institution_url" :errorMsgs="errors.institution_url" 
            label="Institution URL" :required="config.institution_url">
        </c-input>
        <c-edit-degrees :value="degrees" @create="degrees.push($event)" @remove="degrees.splice($event, 1)" 
            @modify="degrees.splice($event.index, 1, $event.value)" name="degrees" :errorMsgs="errors.degrees"
            label="Degrees" help="The institution and name of the degrees you recieved" :required="config.degrees">
        </c-edit-degrees>
        <c-tagger v-model="keywords" name="keywords" :errorMsgs="errors.keywords" label="Keywords" 
            :required="config.keywords">
        </c-tagger>
        <c-message-display :messages="statusMessages">
        </c-message-display>
        <button type="button" class="mt-3 btn btn-primary" @click="createOrUpdate">Save</button>
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
    private api = new ProfileAPI();
    @Prop
    _username: string | null;

    detailPageUrl(state) {
        this.state.username = state.username;
        return this.api.detailUrl(this.state.username);
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
        return this.api.update(this.state.username, new HandlerWithRedirect(this));
    }

    retrieve(username: string) {
        return this.api.retrieve(username).then(r => this.state = r.data);
    }

    async uploadImage(event) {
        const file = event.target.files[0];
        const response = await this.api.uploadProfilePicture({username: this.state.username}, file);
        this.state.avatar = response.data;
    }

    get uploadImageURL() {
        return `${window.location.href}picture/`;
    }
}
