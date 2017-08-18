import { Prop, Component, Watch } from 'vue-property-decorator'
import * as Vue from 'vue'
import { CalendarEvent, CodebaseContributor, Contributor, emptyContributor, emptyReleaseContributor } from '../../store/common'
import { api, api_base } from 'api/index'
import { store } from './store'
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

const listContributors = _.debounce((state, self) => api.contributors.list(state).then(data => self.matchingContributors = data.results), 800);

const contributorSchema = yup.object().shape({
    user: yup.object().shape({
        full_name: yup.string(),
        insitution_name: yup.string(),
        institution_url: yup.string(),
        profile_url: yup.string(),
        username: yup.string()
    }),
    given_name: yup.string().required(),
    family_name: yup.string().required(),
    middle_name: yup.string(),
    affilitions: yup.array().of(yup.string()).min(1),
    type: yup.mixed().oneOf(['person', 'organization'])
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
}

enum FormContributorState {
    list,
    editReleaseContributor,
    editContributor
};

@Component(<any>{
    template: `<div>
        <hr>
        <label class="form-control-label">Current Release Contributors</label>
        <draggable v-model="releaseContributors">
            <ul v-for="releaseContributor in releaseContributors" :key="releaseContributor._id" class="list-group">
                <li class="list-group-item d-flex justify-content-between">
                    {{ releaseContributorLabel(releaseContributor) }}
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
        <div class="row">
            <div class="col-11">
                <small class="text-muted">
                    Click on a release contributor edit and delete buttons to . Drag and drop release contributors to change the order in which they appear. 
                    Main release contributors at the top. Create a new contributor by clicking the add button below.
                </small>
            </div>
            <div class="col-1">
                <button class="btn btn-primary pull-right" type="button" @click="editReleaseContributor()"><span class="fa fa-plus"></span></button>
            </div>
        </div>
        <div class="card" v-if="matchesState(['editReleaseContributor', 'editContributor'])">
            <div class="card-header">
                Release Contributor
            </div>
            <div class="card-body">
                <div :class="['form-group', contributorPresenceError ? 'child-is-invalid' : '' ]">
                    <label class="form-control-label">Contributor</label>
                    <div class="row">
                        <div class="col-11">
                            <multiselect
                                v-model="formContributor"
                                :custom-label="contributorLabel"
                                label="family_name"
                                track-by="id"
                                placeholder="Type to find contributor"
                                :allow-empty="true"
                                :options="matchingContributors"
                                :loading="isLoadingContributors"
                                :searchable="true"
                                :internal-search="false"
                                :options-limit="50"
                                :limit="20"
                                :disabled="matchesState(['editContributor'])"
                                @search-change="fetchMatchingContributors">
                            </multiselect>
                        </div>
                        <div class="col-1">
                            <button type="button" class="btn btn-primary" @click="editContributor()"><span class="fa fa-plus"></span></button>
                        </div>
                    </div>
                    <div class="invalid-feedback" v-show="contributorPresenceError">
                        {{ contributorPresenceError }}
                    </div>
                </div>
                <div v-if="matchesState(['editContributor'])" class="card">
                    <div class="card-header">
                        Create a contributor
                    </div>
                    <div class="card-body">
                        <c-username name="username" v-model="releaseContributor.contributor.user" label="User Name" help="Find a matching user here">
                        </c-username>
                        <c-input name="given_name" v-model="releaseContributor.contributor.given_name" label="Given Name" :errorMsgs="contributorValidationErrors.given_name">
                        </c-input>
                        <c-input name="middle_name" v-model="releaseContributor.contributor.middle_name" label="Middle Name">
                        </c-input>
                        <c-input name="family_name" v-model="releaseContributor.contributor.family_name" label="Family Name" :errorMsgs="contributorValidationErrors.family_name">
                        </c-input>
                        <c-edit-affiliations :value="releaseContributor.contributor.affiliations"
                            @create="releaseContributor.contributor.affiliations.push($event)" 
                            @remove="releaseContributor.contributor.affiliations.splice($event, 1)" 
                            @modify="releaseContributor.contributor.affiliations.splice($event.index, 1, $event.value)"
                            name="affiliations" placeholder="Add affiliation" :errorMsgs="contributorValidationErrors.affiliations">
                            <label class="form-control-label" slot="label">Affiliations</label>
                            <small class="form-text text-muted" slot="help">The institution(s) and other groups you are affiliated with</small>
                        </c-edit-affiliations>
                        <c-input type="select" name="type" v-model="releaseContributor.contributor.type" label="Contributor Type">
                        </c-input>
                        <button type="button" class="btn btn-primary" @click="saveContributor">Save</button>
                        <button type="button" class="btn btn-primary" @click="cancelContributor">Cancel</button>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-control-label">Role</label>
                    <multiselect name="roles" 
                        v-model="releaseContributor.roles"
                        :multiple="true"
                        :custom-label="roleLabel"
                        :close-on-select="false" 
                        placeholder="Type to select role" 
                        :options="roleOptions">
                    </multiselect>
                </div>
                <button type="button" class="btn btn-primary" @click="saveReleaseContributor">Save</button>
                <button type="button" class="btn btn-primary" @click="cancelReleaseContributor">Cancel</button>
            </div>
        </div>
        <button type="button" class="btn btn-primary" @click="save">Save</button>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-edit-affiliations': EditItems,
        'c-message-display': MessageDisplay,
        'c-input': Input,
        'c-username': Username,
        draggable,
        Multiselect,
    }
})
class EditContributors extends Vue {
    initialize() {
        this.releaseContributors = this.$store.state.release.release_contributors.map(rc => _.extend({}, rc));
    }

    created() {
        this.initialize();
    }

    state: FormContributorState = FormContributorState.list;
    
    releaseContributors: Array<CodebaseContributor> = [];
    releaseContributor: CodebaseContributor = emptyReleaseContributor();
    releaseContributorErrors = {};

    contributor: Contributor = emptyContributor(true);
    contributorPresenceError: string = '';
    contributorValidationErrors = {
        family_name: [],
        given_name: [],
    }
    message: string = '';

    isLoadingContributors: boolean = false;
    matchingContributors: Array<Contributor> = [];

    roleOptions: Array<string> = Object.keys(roleLookup);

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
            if (FormContributorState[state] === this.state) {
                return true;
            }
        }
        return false;
    }

    validationErrors(schemaPath: string) {
        return this.releaseContributorErrors[schemaPath] || [];
    }

    validate(schemaPath: string, value) {
        const schema = yup.reach(contributorSchema, schemaPath);
        schema.validate(value).catch(err => this.releaseContributorErrors[schemaPath] = err.errors);
    }

    fetchMatchingContributors(searchQuery: string) {
        listContributors.cancel();
        listContributors({ family_name: searchQuery }, this);
    }

    contributorLabel(contributor: Contributor) {
        let name = [contributor.given_name, contributor.family_name].filter(el => !_.isEmpty(el)).join(' ');
        if (!_.isNull(contributor.user)) {
            name = name === '' ? contributor.user.full_name : name;
            const username = contributor.user.username;
            
            return !_.isNull(username) ? `${name} (${contributor.user.username})`: name; 
        }
        return name;
    }

    _assertState(states: Array<FormContributorState>) {
        if (_.findIndex(states, (state) => this.state === state) === -1) {
            console.error(`AssertionFailed: Actual '${FormContributorState[this.state]}' not in Possible states ${_.map(states, state => FormContributorState[this.state])}`)
        }
    }

    save() {
        const { identifier, version_number } = this.identity;
        api_base.put(`/codebases/${identifier}/releases/${version_number}/contributors/`, this.releaseContributors)
            .catch(err => this.message = 'Submission Error')
            .then(response => this.$store.dispatch('getCodebaseRelease', {identifier, version_number}))
            .then(_ => this.initialize());
    }

    // Release Contributor

    createOrReplaceReleaseContributor(release_contributor: CodebaseContributor) {
        const ind = _.findIndex(this.releaseContributors, rc => release_contributor._id === rc._id);
        if (ind !== -1) {
            this.releaseContributors[ind] = _.merge({}, release_contributor);
        } else {
            this.releaseContributors.push(_.merge({}, release_contributor));
        }
    }

    editReleaseContributor(releaseContributor?: CodebaseContributor) {
        this._assertState([FormContributorState.list]);
        if (releaseContributor === undefined) {
            this.releaseContributor = emptyReleaseContributor()
        } else {
            this.releaseContributor = _.merge({}, releaseContributor);
        }
        this.state = FormContributorState.editReleaseContributor;
    }

    cancelReleaseContributor() {
        this._assertState([FormContributorState.editReleaseContributor, FormContributorState.editContributor]);
        this.releaseContributor = emptyReleaseContributor();
        this.state = FormContributorState.list;
    }

    saveReleaseContributor() {
        this._assertState([FormContributorState.editReleaseContributor, FormContributorState.editContributor]);
        this.createOrReplaceReleaseContributor(this.releaseContributor);
        this.releaseContributor = emptyReleaseContributor();
        this.state = FormContributorState.list;
    }    

    deleteReleaseContributor(_id: string) {
        const index = _.findIndex(this.releaseContributors, rc => rc._id === _id);
        this.releaseContributors.splice(index, 1);
    }

    // Contributor

    get formContributor() {
        /* Vue-Multiselect needs object to be null to display placeholder text contributor is inspected for validity to 
        decide whether or not to return null */
        if (!_.isUndefined(this.releaseContributor.contributor.valid) &&
            !this.releaseContributor.contributor.valid) {
            return null;
        } else {
            return this.releaseContributor.contributor;
        }
    }

    set formContributor(contributor: any) {
        if (!_.isNull(contributor)) {
            this.$set(this.releaseContributor, 'contributor', contributor);
        }
    }

    validateFamilyName(family_name: string): Promise<boolean> {
        const familyNameSchema = yup.reach(contributorSchema, 'family_name',);
        return familyNameSchema.validate(family_name)
            .then(_ => {
                this.contributorValidationErrors.family_name = [];
                return false;
            })
            .catch(err => {
                this.contributorValidationErrors.family_name = err.errors;
                return true;
            });
    }

    validateGivenName(given_name: string): Promise<boolean> {
        const familyNameSchema = yup.reach(contributorSchema, 'given_name');
        return familyNameSchema.validate(given_name)
            .then(_ => { 
                this.contributorValidationErrors.given_name = []
                return false;
            })
            .catch(err => {
                this.contributorValidationErrors.given_name = err.errors;
                return true;
            }); 
    }

    validateContributorPresence(contributor: Contributor | null): boolean {
        if (_.isNull(contributor)) {
            this.contributorPresenceError = 'Contributor must be set'
            return true;
        } else {
            this.contributorPresenceError = '';
            return false;
        }
    }

    isValidContributor(): Promise<boolean> {
        return Promise.all([
            this.validateFamilyName(this.releaseContributor.contributor.family_name),
            this.validateGivenName(this.releaseContributor.contributor.given_name),
        ]).then(validations => _.sum(validations) === 0)
    }

    @Watch('releaseContributor.contributor.family_name')
    onFamilyNameChange(family_name: string) {
        this.validateFamilyName(family_name);
    }

    @Watch('releaseContributor.contributor.given_name')
    onGivenNameChange(given_name: string) {
        this.validateGivenName(given_name);
    }

    @Watch('formContributor')
    onContributorChange(contributor: Contributor | null) {
        this.validateContributorPresence(contributor);
    }

    resetContributorErrors() {
        this.contributorValidationErrors.family_name = [];
        this.contributorValidationErrors.given_name = [];
        this.contributorPresenceError = '';
    }

    editContributor(contributor?: Contributor) {
        this._assertState([FormContributorState.editReleaseContributor]);
        if (contributor !== undefined) {
            this.releaseContributor.contributor = contributor;
        }
        this.state = FormContributorState.editContributor;
    }

    cancelContributor() {
        this._assertState([FormContributorState.editContributor]);
        this.resetContributorErrors();
        this.releaseContributor.contributor = emptyContributor();
        this.state = FormContributorState.editReleaseContributor;
    }

    saveContributor() {
        this._assertState([FormContributorState.editContributor]);
        this.isValidContributor().then(is_valid => {
            if (is_valid) {
                this.state = FormContributorState.editReleaseContributor;
            }
        })
    }

}

export default EditContributors;