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
    full_name: yup.string(),
    insitution_name: yup.string(),
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
    type: yup.mixed().oneOf(['person', 'organization'])
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
                    <c-username name="username" v-model="user"
                        :errorMsgs="errors.user"
                        label="User Name" help="Find a matching user here">
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
                        help="The institution(s) and other groups you are affiliated with. Press enter to add.">
                    </c-edit-affiliations>
                    <c-input type="select" name="type" v-model="type" label="Contributor Type" :errorMsgs="errors.type"
                        :required="config.type">
                    </c-input>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" @click="save">Save</button>
                    <button type="button" class="btn btn-primary" @click="cancel">Cancel</button>
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

    cancel() {
        this.$emit('cancel');
    }
}

@Component(<any>{
    template: `<div class="card">
        <div class="card-header">
            Release Contributor
        </div>
        <div class="card-body">
            <div :class="['form-group', errors.contributor.length === 0 ? '' : 'child-is-invalid' ]">
                <label class="form-control-label">Contributor</label>
                <div class="row">
                    <div class="col-11">
                        <multiselect
                            ref="releaseContributorSelect"
                            v-model="contributor"
                            :custom-label="contributorLabel"
                            label="family_name"
                            track-by="id"
                            placeholder="Type to find contributor"
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
                    <div class="col-1">
                        <button type="button" class="btn btn-primary" @click="$emit('editContributor', state.contributor)"><span class="fa fa-plus"></span></button>
                    </div>
                </div>
                <div class="invalid-feedback" v-show="errors.contributor">
                    {{ errors.contributor.join(', ') }}
                </div>
            </div>
            <div :class="['form-group', errors.roles.length === 0 ? '' : 'child-is-invalid' ]">
                <label class="form-control-label">Role</label>
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
            <button type="button" class="btn btn-primary" @click="save">Add</button>
            <button type="button" class="btn btn-primary" @click="cancel">Cancel</button>
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

    @Watch('releaseContributor')
    setFormState(releaseContributor: CodebaseContributor | null) {
        if (!_.isNull(releaseContributor)) {
            (<any>this).replace(releaseContributor);
        } else {
            (<any>this).replace(createDefaultValue(releaseContributorSchema));
        }
    }

    contributorLabel(contributor: Contributor) {
        let name = [contributor.given_name, contributor.family_name].filter(el => !_.isEmpty(el)).join(' ');
        const user = contributor.user;
        if (!_.isNull(user)) {
            name = name === '' ? (<any>user).full_name : name;
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
        (<Vue>this.$refs.releaseContributorSelect).$el.focus();
    }

    async save() {
        await this.validate();
        const msg = _.cloneDeep(this.state);
        this.replace(createDefaultValue(releaseContributorSchema));
        (<Vue>this.$refs.releaseContributorSelect).$el.focus();
        this.$emit('save', msg);
    }
}

@Component(<any>{
    // language=Vue
    template: `<div>
        <label class="form-control-label required">Current Release Contributors</label>
        <draggable v-model="state" v-if="state.length > 0">
            <ul v-for="releaseContributor in state" :key="releaseContributor._id" class="list-group">
                <li class="list-group-item d-flex justify-content-between">
                    <div>
                        <span class="text-muted fa fa-minus-square-o has-pointer-cursor"></span>
                        {{ releaseContributorLabel(releaseContributor) }}
                    </div>
                    <div v-show="matchesState(['list'])">
                        <span class="badge badge-default badge-pill" @click="editReleaseContributor(releaseContributor)">
                            <span class="fa fa-edit"></span>
                        </span>
                        <span class="badge badge-default badge-pill" @click="deleteReleaseContributor(releaseContributor._id)">
                            <span class="fa fa-remove"></span>
                        </span>
                    </div>
                </li>
            </ul>
        </draggable>
        <div class="alert alert-primary" role="alert" v-else>No contributors</div>
        <div>
            <small class="text-muted">
                Click on a release contributor edit and delete buttons to . Drag and drop release contributors to change the order in which they appear. 
                Main release contributors at the top. Create a new contributor by clicking the add button below.
            </small>
        </div>
        <c-edit-release-contributor :releaseContributor="releaseContributor"
                @save="saveReleaseContributor" @cancel="cancelReleaseContributor" ref="releaseContributor"
                @editContributor="editContributor">
        </c-edit-release-contributor>
        <c-message-display :messages="statusMessages" />
        <button type="button" class="btn btn-primary" @click="save">Save</button>
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
        this.state = this.$store.state.release.release_contributors.map(rc => _.extend({}, rc));
    }

    created() {
        this.initialize();
    }

    formState: FormContributorState = FormContributorState.list;

    statusMessages: Array<{ classNames: string, message}> = [];
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

    // Release Contributor

    createOrReplaceReleaseContributor(release_contributor: CodebaseContributor) {
        const ind = _.findIndex(this.state, rc => release_contributor._id === rc._id);
        if (ind !== -1) {
            this.state[ind] = _.merge({}, release_contributor);
        } else {
            this.state.push(_.merge({'_id': _.uniqueId()}, release_contributor));
        }
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
    }

    saveReleaseContributor(releaseContributor) {
        this.createOrReplaceReleaseContributor(releaseContributor);
        this.releaseContributor = null;
        this.formState = FormContributorState.list;
    }

    deleteReleaseContributor(_id: string) {
        const index = _.findIndex(this.state, rc => rc._id === _id);
        this.state.splice(index, 1);
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
