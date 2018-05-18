import {Prop, Component, Watch} from 'vue-property-decorator'
import Vue from 'vue'
import {
    CalendarEvent, CodebaseContributor, Contributor, emptyContributor, emptyReleaseContributor,
    User
} from 'store/common'
import {CodebaseReleaseAPI, ContributorAPI} from 'api'
import {store} from './store'
import Checkbox from 'components/forms/checkbox'
import Datepicker from 'components/forms/datepicker'
import Input from 'components/forms/input'
import Markdown from 'components/forms/markdown'
import MessageDisplay from 'components/message_display'
import EditItems from 'components/edit_items'
import Multiselect from 'vue-multiselect'
import Username from 'components/username'
import * as draggable from 'vuedraggable'
import * as _ from 'lodash'
import * as yup from 'yup'
import {createDefaultValue, createFormValidator} from 'pages/form'
import * as _$ from 'jquery'
import {HandlerShowSuccessMessage} from "api/handler";

const $: any = _$;

const codebaseReleaseAPI = new CodebaseReleaseAPI();

const listContributors = _.debounce(async (state, self) => {
    self.isLoading = true;
    try {
        const response = await ContributorAPI.list(state);
        self.matchingContributors = response.data.results;
        self.isLoading = false;
    } catch (e) {
        self.isLoading = false;
        console.error(e);
    }
}, 800);

const userSchema = yup.object().shape({
    name: yup.string(),
    institution_name: yup.string(),
    institution_url: yup.string(),
    profile_url: yup.string(),
    username: yup.string()
});

const contributorSchema = yup.object().shape({
    user: yup.mixed().test('is-not-null', '${path} must have a value', value => !_.isNull(value)).label('this'),
    email: yup.string().email().required(),
    given_name: yup.string().required(),
    family_name: yup.string().required(),
    middle_name: yup.string(),
    affiliations: yup.array().of(yup.string()).min(1).required(),
    type: yup.string().oneOf(['person', 'organization']).default('person')
});

export const releaseContributorSchema = yup.object().shape({
    contributor: yup.mixed().test('is-not-null', '${path} must have a value', value => !_.isNull(value)).label('this'),
    roles: yup.array().of(yup.string()).min(1).label('affiliations')
});

const roleLookup = {
    author: 'Author',
    publisher: 'Publisher',
    resourceProvider: 'Resource Provider',
    maintainer: 'Maintainer',
    pointOfContact: 'Point of Contact',
    editor: 'Editor',
    contributor: 'Contributor',
    collaberator: 'Collaborator',
    funder: 'Funder',
    copyrightholder: 'Copyright Holder'
};

enum FormContributorState {
    list,
    editReleaseContributor,
    editContributor
};

@Component(<any>{
    template: `<div class="modal" id="createContributorForm">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Create a contributor</h5>
                </div>
                <div class="modal-body">
                    <c-username name="username" v-model="user" @input="setUserDefaults"
                        :errorMsgs="errors.user"
                        label="Name" help="Type to search for matching users here (searches name and email)">
                    </c-username>
                    <c-input name="given_name" v-model="given_name" label="Given Name" :errorMsgs="errors.given_name"
                        :required="config.given_name">
                    </c-input>
                    <c-input name="middle_name" v-model="middle_name" label="Middle Name" :errorMsgs="errors.middle_name" 
                        :required="config.middle_name">
                    </c-input>
                    <c-input name="family_name" v-model="family_name" label="Family Name" :errorMsgs="errors.family_name"
                        :required="config.family_name">
                    </c-input>
                    <c-input name="email" v-model="email" label="Email Address" :errorMsgs="errors.email"
                        :required="config.email">
                    </c-input>
                    <c-edit-affiliations :value="affiliations.map(x => x.name)"
                        @create="affiliations.push({ 'name': $event})"
                        @remove="affiliations.splice({ 'name': $event}, 1)"
                        @modify="affiliations.splice($event.index, 1, { 'name': $event.value })"
                        name="affiliations" placeholder="Add affiliation"
                        :errorMsgs="errors.affiliations"
                        :required="config.affiliations"
                        label="Affiliations"
                        help="The institution(s) this contributor is affiliated with. You must press enter to add an affiliation.">
                    </c-edit-affiliations>
                    <label for="contributorType" class="form-control-label">
                        Contributor Type
                    </label>
                    <select name="type" v-model="type" class="form-control" id="contributorType">
                        <option>person</option>
                        <option>organization</option>
                    </select>
                    <div v-if="errors.type.length > 0" class="invalid-feedback-always">{{ errors.type.join(', ') }}</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary mr-auto" @click="save">Save</button>
                    <button type="button" class="btn btn-secondary" @click="cancel">Cancel</button>
                </div>
            </div>
        </div>
    </div>`,
    components: {
        'c-edit-affiliations': EditItems,
        'c-input': Input,
        'c-username': Username,
    },
})
class EditContributor extends createFormValidator(contributorSchema) {
    @Prop()
    active: boolean;

    @Prop()
    contributor;

    @Watch('contributor')
    setFormState(contributor: Contributor | null) {
        if (!_.isEmpty(contributor)) {
            (<any>this).replace(contributor);
        } else {
            (<any>this).replace(createDefaultValue(contributorSchema));
        }
    }

    async save() {
        await this.validate();
        this.$emit('save', this.state);
    }

    setUserDefaults(user) {
        this.state.given_name = this.state.given_name || user.given_name;
        this.state.family_name = this.state.family_name || user.family_name;
        this.state.email = this.state.email || user.email;
        this.state.type = this.state.type || user.type;
        if (_.isEmpty(this.state.affiliations) && user.institution_name) {
            this.state.affiliations = [{ name: user.institution_name }];
        }
    }

    cancel() {
        this.$emit('cancel');
    }
}

@Component(<any>{
    template: `<div class="card mt-2">
        <div class="card-header">
            <h5 class='card-title'>Add or edit a Release Contributor</h5>
        </div>
        <div class="card-body">
            <div :class="['form-group', errors.contributor.length === 0 ? '' : 'child-is-invalid' ]">
                <div class="row">
                    <div class="col-9">
                        <multiselect
                            v-model="contributor"
                            :custom-label="contributorLabel"
                            label="family_name"
                            track-by="id"
                            placeholder="Type to find a contributor previously entered in our system"
                            :allow-empty="true"
                            :options="matchingContributors"
                            :loading="isLoading"
                            :searchable="true"
                            :internal-search="false"
                            :options-limit="50"
                            :limit="20"
                            @search-change="fetchMatchingContributors">
                        </multiselect>
                    </div>
                    <div class="col-3">
                        <button class="btn btn-block btn-primary" @click="$emit('editContributor', state.contributor)"><i class='fa fa-plus'></i> Add a new contributor</button>
                    </div>
                </div>
                <div class="invalid-feedback" v-show="errors.contributor">
                    {{ errors.contributor.join(', ') }}
                </div>
            </div>
            <div :class="['form-group', errors.roles.length === 0 ? '' : 'child-is-invalid' ]">
                <multiselect name="roles" 
                    v-model="roles"
                    :multiple="true"
                    :custom-label="roleLabel"
                    :close-on-select="false" 
                    placeholder="Type to select role" 
                    :options="roleOptions">
                </multiselect>
                <div class="invalid-feedback" v-show="errors.roles">
                    {{ errors.roles.join(', ') }}
                </div>
            </div>
            <button type="button" class="btn btn-primary" @click="save"><i class='fa fa-user-plus'></i> Register citable contributor</button>
            <button type="button" class="btn btn-secondary" @click="cancel">Cancel</button>
        </div>
    </div>`,
    components: {
        Multiselect
    },
})
class EditReleaseContributor extends createFormValidator(releaseContributorSchema) {
    @Prop()
    releaseContributor;

    isLoading: boolean = false;
    matchingContributors: Array<Contributor> = [];
    roleOptions: Array<string> = Object.keys(roleLookup);

    @Watch('releaseContributor', { immediate: true, deep: true })
    setFormState(releaseContributor: CodebaseContributor | null) {
        if (!_.isNull(releaseContributor)) {
            (<any>this).replace(releaseContributor);
        } else {
            (<any>this).replace(createDefaultValue(releaseContributorSchema));
            (<any>this).state.contributor = createDefaultValue(contributorSchema);
        }
    }

    contributorLabel(contributor: Contributor) {
        let name = [contributor.given_name, contributor.family_name].filter(el => !_.isEmpty(el)).join(' ');
        const user = contributor.user;
        if (!_.isNull(user)) {
            name = name === '' ? (<any>user).name : name;
            const username = (<any>user).username;

            return !_.isNull(username) ? `${name} (${username})` : name;
        }
        return name;
    }

    roleLabel(value: string) {
        return roleLookup[value] || value;
    }

    fetchMatchingContributors(searchQuery: string) {
        listContributors.cancel();
        listContributors({query: searchQuery}, this);
    }

    cancel() {
        this.$emit('cancel');
        this.replace(createDefaultValue(releaseContributorSchema));
    }

    async save() {
        await this.validate();
        const msg = _.cloneDeep(this.state);
        this.replace(createDefaultValue(releaseContributorSchema));
        msg.edited = true;
        this.$emit('save', msg);
    }
}

@Component(<any>{
    // language=Vue
    template: `<div>
        <p class='mt-3'>
            Please list the contributors that should be included in a citation for this software release. Ordering is
            important, as is the role of the contributor. You can drag and drop release contributors via the 
            <i class='fa fa-exchange'></i> button to change the order in which they appear, edit them <i class='fa fa-edit'></i>, or
            remove them <i class='fa fa-remove'></i>.
        </p>
        <p>By default, we will always add the submitter (you) as a release contributor. There must be at least one
        contributor for a given release. Make sure you click "Save" after you're done making changes. Unsaved release
        contributors display in yellow.
        </p>
        <label class="form-control-label required">Current Release Contributors</label>
        <draggable v-model="state" v-if="state.length > 0" @end="refreshStatusMessage">
            <ul v-for="releaseContributor in state" :key="releaseContributor._id" class="list-group">
                <li :class="['list-group-item d-flex justify-content-between', { 'list-group-item-warning': releaseContributor.edited}]">
                    <div>
                        <span class="btn btn-sm fa fa-exchange"></span>
                        {{ releaseContributorLabel(releaseContributor) }}
                    </div>
                    <div v-show="matchesState(['list'])">
                        <span class="btn btn-sm" @click="editReleaseContributor(releaseContributor)">
                            <span class="fa fa-edit"></span>
                        </span>
                        <span class="btn btn-sm" @click="deleteReleaseContributor(releaseContributor._id)">
                            <span class="fa fa-remove"></span>
                        </span>
                    </div>
                </li>
            </ul>
        </draggable>
        <div class="alert alert-primary" role="alert" v-else>No contributors</div>
        <button class="mt-2 btn btn-primary" ref="saveReleaseContributorsBtn" @click="save">Save</button>
        <c-message-display :messages="statusMessages" @clear="statusMessages = []" />
        <hr>
        <div class='mt-2'>
            You can add new contributors via the form below. If you can't find an existing Contributor in our system,
            you can add a new one via the 
            <button class='btn btn-primary btn-sm'><i class='fa fa-plus'></i></button> button. After you've selected a contributor, click the 
            <button class='btn btn-sm btn-primary'><i class='fa fa-user-plus'></i> Register</button> button to register
            them as a cited contributor to this release.
        </div>
        <c-edit-release-contributor :releaseContributor="releaseContributor"
                @save="saveReleaseContributor" @cancel="cancelReleaseContributor" ref="releaseContributor"
                @editContributor="editContributor">
        </c-edit-release-contributor>
        <c-edit-contributor :contributor="contributor" ref="contributor"
                            @save="saveContributor" @cancel="cancelContributor">
        </c-edit-contributor>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-edit-affiliations': EditItems,
        'c-message-display': MessageDisplay,
        'c-input': Input,
        'c-username': Username,
        'c-edit-release-contributor': EditReleaseContributor,
        'c-edit-contributor': EditContributor,
        draggable,
        Multiselect,
    }
})
class EditContributors extends Vue {
    @Prop()
    initialData: object;

    initialize() {
        this.initialState = this.$store.state.release.release_contributors.map(rc => _.extend({}, rc))
        this.state = _.cloneDeep(this.initialState);
    }

    created() {
        this.initialize();
    }

    formState: FormContributorState = FormContributorState.list;

    statusMessages: Array<{ classNames: string, message}> = [];
    initialState: Array<CodebaseContributor> = [];
    state: Array<CodebaseContributor> = [];
    releaseContributor: CodebaseContributor | null = null;
    contributor: Contributor | null = null;

    message: string = '';

    releaseContributorLabel(releaseContributor: CodebaseContributor) {
        const name = [releaseContributor.contributor.given_name, releaseContributor.contributor.family_name].join(' ');
        const roles = releaseContributor.roles.length > 0 ? ` (${releaseContributor.roles.map(this.roleLabel).join(', ')})` : '';
        return `${name}${roles}`
    }

    roleLabel(value: string) {
        return roleLookup[value] || value;
    }

    get identity() {
        return this.$store.getters.identity;
    }

    matchesState(states: Array<keyof typeof FormContributorState>) {
        console.assert(states.length > 0);
        for (const state of states) {
            if (FormContributorState[state] === this.formState) {
                return true;
            }
        }
        return false;
    }

    validate() {
        return Promise.resolve(true);
    }

    async save() {
        const {identifier, version_number} = this.identity;
        const response = await codebaseReleaseAPI.updateContributors({
            identifier,
            version_number
        }, new HandlerShowSuccessMessage(this));
        await this.$store.dispatch('getCodebaseRelease', {identifier, version_number});
        this.initialize();
    }

    refreshStatusMessage() {
        if (!_.isEqual(this.state, this.initialState)) {
            this.statusMessages = [
                {classNames: 'alert alert-warning', message: 'You have unsaved contributor modifications'}
            ];
        } else {
            this.statusMessages = [];
        }
    }

    // Release Contributor

    createOrReplaceReleaseContributor(release_contributor: CodebaseContributor) {
        const ind = _.findIndex(this.state, rc => release_contributor._id === rc._id);
        if (ind !== -1) {
            this.state[ind] = _.merge({}, release_contributor);
        } else {
            this.state.push(_.merge({'_id': _.uniqueId()}, release_contributor));
        }
        this.refreshStatusMessage();
    }

    editReleaseContributor(releaseContributor?: CodebaseContributor) {
        if (_.isUndefined(releaseContributor)) {
            this.releaseContributor = null;
        } else {
            this.releaseContributor = _.merge({}, releaseContributor);
        }
        this.formState = FormContributorState.editReleaseContributor;
    }

    cancelReleaseContributor() {
        this.formState = FormContributorState.list;
        (<any>this.$refs.saveReleaseContributorsBtn).focus();
    }

    saveReleaseContributor(releaseContributor) {
        this.createOrReplaceReleaseContributor(releaseContributor);
        this.releaseContributor = null;
        this.formState = FormContributorState.list;
        (<any>this.$refs.saveReleaseContributorsBtn).focus();
    }

    isExistingReleaseContributor(releaseContributor) {
        return !_.isUndefined(releaseContributor.index);
    }

    deleteReleaseContributor(_id: string) {
        const index = _.findIndex(this.state, rc => rc._id === _id);
        this.state.splice(index, 1);
        this.refreshStatusMessage();
    }

    // Contributor

    editContributor(contributor: Contributor) {
        this.contributor = _.merge({}, contributor);
        $('#createContributorForm').modal('show');
        this.formState = FormContributorState.editContributor;
    }

    cancelContributor() {
        $('#createContributorForm').modal('hide');
        this.formState = FormContributorState.editReleaseContributor;
    }

    saveContributor(contributor: Contributor) {
        this.formState = FormContributorState.editReleaseContributor;
        $('#createContributorForm').modal('hide');
        if (_.isNull(this.releaseContributor)) {
            this.releaseContributor = createDefaultValue(releaseContributorSchema);
        }
        (<any>this).releaseContributor.contributor = _.merge({}, contributor);
    }

}

export default EditContributors;
