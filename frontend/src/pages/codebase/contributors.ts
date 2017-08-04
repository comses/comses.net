import { Prop, Component, Watch } from 'vue-property-decorator'
import * as Vue from 'vue'
import { CalendarEvent, CodebaseContributor, Contributor, emptyContributor, emptyReleaseContributor } from '../../store/common'
import { api } from 'api/index'
import { store, contributorSchema } from './store'
import Checkbox from 'components/forms/checkbox.vue'
import Datepicker from 'components/forms/datepicker.vue'
import Input from 'components/forms/input.vue'
import Markdown from 'components/forms/markdown.vue'
import MessageDisplay from 'components/message_display.vue'
import EditItems from 'components/edit_items.vue'
import Multiselect from 'vue-multiselect'
import Username from 'components/username.vue'
import * as draggable from 'vuedraggable'
import * as _ from 'lodash'
import * as yup from 'yup'

const listContributors = _.debounce((state, self) => api.contributors.list(state).then(data => self.matchingContributors = data.results), 800);

const roleOptions: Array<{ value: string, label: string }> = [
    { value: 'author', label: 'Author' },
    { value: 'publisher', label: 'Publisher' },
    { value: 'resourceProvider', label: 'Resource Provider' },
    { value: 'maintainer', label: 'Maintainer' },
    { value: 'pointOfContact', label: 'Point of Contact' },
    { value: 'editor', label: 'Editor' },
    { value: 'contributor', label: 'Contributor' },
    { value: 'collaborator', label: 'Collaborator' },
    { value: 'funder', label: 'Funder' },
    { value: 'copyrightholder', label: 'Copyright Holder' }
];

enum FormContributorState {
    list,
    editReleaseContributor,
    editContributor
};

@Component(<any>{
    template: `<div>
        <hr>
        <label class="form-control-label">Current Contributors</label>
        <draggable v-model="releaseContributors">
            <ul v-for="releaseContributor in releaseContributors" :key="releaseContributor._id" class="list-group">
                <li class="list-group-item justify-content-between">
                    {{ releaseContributor.contributor.given_name }} {{ releaseContributor.contributor.family_name }} ({{ releaseContributor.role }})
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
            <div class="card-block">
                <div :class="['form-group', contributorPresenceError ? 'has-danger' : '' ]">
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
                    <div class="form-control-feedback form-control-danger" v-show="contributorPresenceError">
                        {{ contributorPresenceError }}
                    </div>
                </div>
                <div v-if="matchesState(['editContributor'])" class="card">
                    <div class="card-header">
                        Create a contributor
                    </div>
                    <div class="card-block">
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
                            name="affiliations" placeholder="Add affiliation">
                            <label class="form-control-label" slot="label">Affiliations</label>
                            <small class="form-text text-muted" slot="help">The institution(s) and other groups you are affiliated with</small>
                        </c-edit-affiliations>
                        <c-input type="select" name="type" v-model="releaseContributor.contributor.type" label="Contributor Type">
                        </c-input>
                        <button type="button" class="btn btn-primary" @click="saveContributor">Save</button>
                        <button type="button" class="btn btn-primary" @click="cancelContributor">Cancel</button>
                    </div>
                </div>
                <c-checkbox name="is_maintainer" label="Is Maintainer?" v-model="releaseContributor.is_maintainer" :errorMsgs="validationErrors('is_maintainer')">
                </c-checkbox>
                <c-checkbox type="checkbox" name="is_rights_holder" label="Is Rights Holder?" v-model="releaseContributor.is_rights_holder" :errorMsgs="validationErrors('is_rights_holder')">
                </c-checkbox>
                <div class="form-group">
                    <label class="form-control-label">Role</label>
                    <multiselect name="role" 
                        v-model="role"
                        label="label" 
                        track-by="value" 
                        placeholder="Type to select role" 
                        :options="roleOptions">
                    </multiselect>
                </div>
                <button type="button" class="btn btn-primary" @click="saveReleaseContributor">Save</button>
                <button type="button" class="btn btn-primary" @click="cancelReleaseContributor">Cancel</button>
            </div>
        </div>
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
    state: FormContributorState = FormContributorState.list;
    
    releaseContributor: CodebaseContributor = emptyReleaseContributor();
    releaseContributorErrors = {};

    contributor: Contributor = emptyContributor(true);
    contributorPresenceError: string = '';
    contributorValidationErrors = {
        family_name: [],
        given_name: [],
    }


    isLoadingContributors: boolean = false;
    matchingContributors: Array<Contributor> = [];
    roleOptions: Array<{ value: string, label: string }> = [
        { value: 'author', label: 'Author' },
        { value: 'publisher', label: 'Publisher' },
        { value: 'resourceProvider', label: 'Resource Provider' },
        { value: 'maintainer', label: 'Maintainer' },
        { value: 'pointOfContact', label: 'Point of Contact' },
        { value: 'editor', label: 'Editor' },
        { value: 'contributor', label: 'Contributor' },
        { value: 'collaborator', label: 'Collaborator' },
        { value: 'funder', label: 'Funder' },
        { value: 'copyrightholder', label: 'Copyright Holder' }
    ];

    get role() {
        return <any>_.find(this.roleOptions, roleOption => roleOption.value === (<any>this.releaseContributor).role);
    }

    set role(roleOption: { label: string, value: string}) {
        this.releaseContributor.role = roleOption.value;
    }

    get releaseContributors() {
        return this.$store.state.release.release_contributors;
    }

    set releaseContributors(value) {
        this.$store.commit('setReleaseContributors', value);
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
        let name = [contributor.given_name, contributor.family_name].filter(el => _.isEmpty(el)).join(' ');
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

    // Release Contributor

    editReleaseContributor(releaseContributor?: CodebaseContributor) {
        this._assertState([FormContributorState.list]);
        if (releaseContributor === undefined) {
            this.releaseContributor = emptyReleaseContributor()
        } else {
            this.releaseContributor = _.extend({}, releaseContributor);
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
        this.$store.commit('createOrReplaceReleaseContributor', this.releaseContributor);
        this.releaseContributor = emptyReleaseContributor();
        this.state = FormContributorState.list;
    }    

    deleteReleaseContributor(_id: string) {
        this.$store.commit('deleteReleaseContributor', _id);
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