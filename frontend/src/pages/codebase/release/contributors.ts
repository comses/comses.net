import {Prop, Component, Watch} from 'vue-property-decorator';
import Vue from 'vue';
import {
    CalendarEvent, CodebaseContributor, Contributor, emptyContributor, emptyReleaseContributor,
    User,
} from '@/store/common';
import {CodebaseReleaseAPI, ContributorAPI} from '@/api';
import Checkbox from '@/components/forms/checkbox';
import Input from '@/components/forms/input';
import MessageDisplay from '@/components/messages';
import EditItems from '@/components/textitem';
import Multiselect from 'vue-multiselect';
import Username from '@/components/username';
import draggable from 'vuedraggable';
import * as _ from 'lodash';
import * as yup from 'yup';
import * as _$ from 'jquery';
import {createDefaultValue, createFormValidator} from '@/pages/form';
import 'bootstrap/js/dist/modal';
import {HandlerShowSuccessMessage} from '@/api/handler';


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
    username: yup.string(),
});

const contributorSchema = yup.object().shape({
    user: yup.mixed().nullable(),
    email: yup.string().email().required(),
    given_name: yup.string().required(),
    family_name: yup.string().required(),
    middle_name: yup.string(),
    affiliations: yup.array().of(yup.string()).min(1).required(),
    type: yup.string().oneOf(['person', 'organization']).default('person'),
});

export const releaseContributorSchema = yup.object().shape({
    contributor: yup.mixed().test('is-not-null', '${path} must have a value', (value) => !_.isNull(value)).label('this'),
    include_in_citation: yup.boolean().required().default(true),
    roles: yup.array().of(yup.string()).min(1).label('affiliations'),
});

const roleLookup = {
    author: 'Author',
    publisher: 'Publisher',
    resourceProvider: 'Resource Provider',
    maintainer: 'Maintainer',
    pointOfContact: 'Point of Contact',
    editor: 'Editor',
    contributor: 'Contributor',
    collaborator: 'Collaborator',
    funder: 'Funder',
    copyrightholder: 'Copyright Holder',
};

enum FormContributorState {
    list,
    editReleaseContributor,
    editContributor,
}

function displayContributorLabel(contributor: Contributor) {
    let name = [contributor.given_name, contributor.family_name].filter((el) => !_.isEmpty(el)).join(' ');
    name = name.length > 0 ? name : contributor.email;
    const user = contributor.user;
    if (!_.isNull(user)) {
        name = name === '' ? (user as any).name : name;
        const username = (user as any).username;

        return !_.isNull(username) ? `${name} [${username}]` : name;
    }
    return name;
}

@Component({
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
                    <button type="button" class="btn btn-secondary" @click="cancel">Cancel</button>
                    <button type="button" class="btn btn-primary ml-auto" @click="save">Save</button>
                </div>
            </div>
        </div>
    </div>`,
    components: {
        'c-edit-affiliations': EditItems,
        'c-input': Input,
        'c-username': Username,
    },
} as any)
class EditContributor extends createFormValidator(contributorSchema) {
    @Prop()
    public active: boolean;

    @Prop()
    public contributor;

    @Watch('contributor')
    public setFormState(contributor: Contributor | null) {
        if (!_.isEmpty(contributor)) {
            (this as any).replace(contributor);
        } else {
            (this as any).replace(createDefaultValue(contributorSchema));
        }
    }

    public async save() {
        await this.validate();
        this.$emit('save', this.state);
    }

    public setUserDefaults(user) {
        this.state.given_name = this.state.given_name || user.given_name;
        this.state.family_name = this.state.family_name || user.family_name;
        this.state.email = this.state.email || user.email;
        this.state.type = this.state.type || user.type;
        if (_.isEmpty(this.state.affiliations) && user.institution_name) {
            this.state.affiliations = [{name: user.institution_name}];
        }
    }

    public cancel() {
        this.$emit('cancel');
    }
}

@Component({
    template: `<div class="card mt-2">
        <div class="card-header">
            <h5 class='card-title'>Manage contributors for this release</h5>
        </div>
        <div class="card-body">
            <div :class="['form-group', errors.contributor.length === 0 ? '' : 'child-is-invalid' ]">
                <div class="row">
                    <div class="col-9">
                        <multiselect
                            v-model="candidateContributor"
                            :custom-label="contributorLabel"
                            label="family_name"
                            track-by="id"
                            placeholder="Find a contributor previously entered in our system"
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
                        <button class="btn btn-block btn-primary" @click="$emit('edit-contributor', state.contributor)"><i class='fas fa-plus-square'></i> Create a new contributor</button>
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
                    placeholder="Role(s) for this contributor"
                    :options="roleOptions">
                </multiselect>
                <div class="invalid-feedback" v-show="errors.roles">
                    {{ errors.roles.join(', ') }}
                </div>
            </div>
            <div class='form-group'>
              <div class='form-check'>
                <label class='form-check-label'>
                  <input v-model="include_in_citation" class='form-check-input' type='checkbox'>
                  Include in citation?
                </label>
              </div>
              <button type="button" class="btn btn-secondary" @click="cancel" v-show="hasEdits">Cancel</button>
              <button type="button" class="ml-auto btn btn-primary" @click="save"><i class='fas fa-user-plus'></i> Register contributor</button>
            </div>
        </div>
    </div>`,
    components: {
        Multiselect,
    },
} as any)
class EditReleaseContributor extends createFormValidator(releaseContributorSchema) {
    @Prop()
    public releaseContributor;

    public isLoading: boolean = false;
    public matchingContributors: Contributor[] = [];
    public roleOptions: string[] = Object.keys(roleLookup);

    @Watch('releaseContributor', {immediate: true, deep: true})
    public setFormState(releaseContributor: CodebaseContributor | null) {
        if (!_.isNull(releaseContributor)) {
            (this as any).replace(releaseContributor);
        } else {
            (this as any).replace(createDefaultValue(releaseContributorSchema));
            (this as any).state.contributor = createDefaultValue(contributorSchema);
        }
    }

    get candidateContributor() {
        // want to display label if no contributor is selected
        if (this.state.contributor &&
            _.isEmpty(this.state.contributor.email) &&
            _.isEmpty(this.state.contributor.given_name) &&
            _.isEmpty(this.state.contributor.family_name)) {
            return null;
        }
        return this.state.contributor;
    }

    set candidateContributor(contributor: Contributor | null) {
        if (!_.isEmpty(contributor)) {
            (this as any).contributor = contributor;
        }
    }

     get hasEdits(): boolean {
        return !_.isEmpty(this.candidateContributor) || !_.isEmpty((this as any).roles);
    }

    public contributorLabel(contributor: Contributor) {
        return displayContributorLabel(contributor);
    }

    public roleLabel(value: string) {
        return roleLookup[value] || value;
    }

    public fetchMatchingContributors(searchQuery: string) {
        listContributors.cancel();
        listContributors({query: searchQuery}, this);
    }

    public cancel() {
        this.$emit('cancel');
        this.replace(createDefaultValue(releaseContributorSchema));
    }

    public async save() {
        await this.validate();
        const msg = _.cloneDeep(this.state);
        this.replace(createDefaultValue(releaseContributorSchema));
        msg.edited = true;
        this.$emit('save', msg);
    }
}


class ContributorResponseHandler extends HandlerShowSuccessMessage {
    public updateListServerValidationMessage(errors) {
        this.component.statusMessages = _.concat({
                classNames: 'alert alert-danger',
                message: 'Server Side Validation Errors',
            },
            _.zipWith(errors, (this.state as CodebaseContributor[]), (error, releaseContributor) => ({
                releaseContributor,
                error,
            }))
                .filter((value) => !_.isEmpty(value.error))
                .map((value) => {
                    return {
                        classNames: 'alert alert-danger',
                        message: `${displayContributorLabel(value.releaseContributor.contributor)}: ${JSON.stringify(value.error)}`,
                    };
                }));
    }
}

@Component({
    // language=Vue
    template: `<div>
        <p class='mt-3'>
            Please list the contributors that should be included in a citation for this software release. Ordering is
            important, as is the role of the contributor. You can change ordering by using
            <i class='fas fa-exchange-alt'></i> to drag and drop contributors. Editing
            <i class='fas fa-edit'></i> an existing contributor will update the "Manage contributors" form above the
            "Current Release Contributors" area. Remove a contributor by clicking the <i class='fas fa-trash'></i> button.
            Don't forget to click Save to apply your changes.
        </p>
        <p>By default, we will always add the submitter (you) as a release contributor. There must be at least one
        contributor for a given release. Make sure you click "Save" after you're done making changes. Unsaved changes
        are highlighted in yellow.
        </p>
        <div class='mt-2'>
            If you can't find an existing Contributor in our system, make a new one by clicking 
            <button class='btn btn-primary btn-sm'><i class='fas fa-plus-square'></i> Create a new contributor</button>.
            After selecting a contributor, role, and whether they should be included in this software release's citation, click 
            <button class='btn btn-sm btn-primary'><i class='fas fa-user-plus'></i> Register</button> to add them
            to the release contributors list below and then Save.
        </div>
        <c-edit-release-contributor :releaseContributor="releaseContributor"
                @save="saveReleaseContributor" @cancel="cancelReleaseContributor" ref="releaseContributor"
                @edit-contributor="editContributor">
        </c-edit-release-contributor>
        <c-edit-contributor :contributor="contributor" ref="contributor"
                            @save="saveContributor" @cancel="cancelContributor">
        </c-edit-contributor>
        <hr>
        <label class="form-control-label required">Current Release Contributors</label>
        <draggable v-model="state" v-if="state.length > 0" @end="refreshStatusMessage">
            <ul v-for="releaseContributor in state" :key="releaseContributor._id" class="list-group">
                <li :class="['list-group-item d-flex justify-content-between', { 'list-group-item-warning': releaseContributor.edited}]">
                    <div>
                        <span class="btn btn-sm fas fa-exchange-alt"></span>
                        {{ releaseContributorLabel(releaseContributor) }}
                        <span :class="['badge', releaseContributor.include_in_citation ? 'badge-secondary' : 'badge-warning']">
                          {{ releaseContributor.include_in_citation ? 'Citable' : 'Non-citable' }}
                        </span>
                    </div>
                    <div v-show="matchesState(['list'])">
                        <span class="btn btn-sm" @click="editReleaseContributor(releaseContributor)">
                            <span class="fas fa-edit"></span>
                        </span>
                        <span class="btn btn-sm" @click="deleteReleaseContributor(releaseContributor._id)">
                            <span class="fas fa-trash"></span>
                        </span>
                    </div>
                </li>
            </ul>
        </draggable>
        <div class="alert alert-primary" role="alert" v-else>No contributors</div>
        <button class="pull-right mt-2 btn btn-primary" ref="saveReleaseContributorsBtn" @click="save">Save</button>
        <c-message-display :messages="statusMessages" @clear="statusMessages = []" />
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
    },
} as any)
class EditContributors extends Vue {

    get identity() {
        return this.$store.getters.identity;
    }
    @Prop()
    public initialData: object;

    public formState: FormContributorState = FormContributorState.list;

    public statusMessages: Array<{ classNames: string, message }> = [];
    public initialState: CodebaseContributor[] = [];
    public state: CodebaseContributor[] = [];
    public releaseContributor: CodebaseContributor | null = null;
    public contributor: Contributor | null = null;

    public message: string = '';

    public initialize() {
        this.initialState = this.$store.state.release.release_contributors.map((rc) => _.extend({}, rc));
        this.state = _.cloneDeep(this.initialState);
    }

    public created() {
        this.initialize();
    }

    public releaseContributorLabel(releaseContributor: CodebaseContributor) {
        const name = displayContributorLabel(releaseContributor.contributor);
        const roles = releaseContributor.roles.length > 0 ? ` (${releaseContributor.roles.map(this.roleLabel).join(', ')})` : '';
        return `${name}${roles}`;
    }

    public roleLabel(value: string) {
        return roleLookup[value] || value;
    }

    public matchesState(states: Array<keyof typeof FormContributorState>) {
        console.assert(states.length > 0);
        for (const state of states) {
            if (FormContributorState[state] === this.formState) {
                return true;
            }
        }
        return false;
    }

    public validate() {
        return Promise.resolve(true);
    }

    public async save() {
        const {identifier, version_number} = this.identity;
        const response = await codebaseReleaseAPI.updateContributors({
            identifier,
            version_number,
        }, new ContributorResponseHandler(this));
        if (_.isEmpty(response) || response.status < 200 || response.status >= 300) {
            return;
        }
        await this.$store.dispatch('getCodebaseRelease', {identifier, version_number});
        this.initialize();
    }

    public refreshStatusMessage() {
        if (!_.isEqual(this.state, this.initialState)) {
            this.statusMessages = [
                {classNames: 'alert alert-warning', message: 'NOTE: there are unsaved changes to the contributor list. Click Save to apply these changes.'},
            ];
        } else {
            this.statusMessages = [];
        }
    }

    // Release Contributor

    public createOrReplaceReleaseContributor(release_contributor: CodebaseContributor) {
        const ind = _.findIndex(this.state, (rc) => release_contributor._id === rc._id);
        if (ind !== -1) {
            this.state[ind] = _.merge({}, release_contributor);
        } else {
            this.state.push(_.merge({_id: _.uniqueId()}, release_contributor));
        }
        this.refreshStatusMessage();
    }

    public editReleaseContributor(releaseContributor?: CodebaseContributor) {
        if (_.isUndefined(releaseContributor)) {
            this.releaseContributor = null;
        } else {
            this.releaseContributor = _.merge({}, releaseContributor);
        }
        this.formState = FormContributorState.editReleaseContributor;
    }

    public cancelReleaseContributor() {
        this.formState = FormContributorState.list;
        (this.$refs.saveReleaseContributorsBtn as any).focus();
    }

    public saveReleaseContributor(releaseContributor) {
        this.createOrReplaceReleaseContributor(releaseContributor);
        this.releaseContributor = null;
        this.formState = FormContributorState.list;
        (this.$refs.saveReleaseContributorsBtn as any).focus();
    }

    public isExistingReleaseContributor(releaseContributor) {
        return !_.isUndefined(releaseContributor.index);
    }

    public deleteReleaseContributor(_id: string) {
        const index = _.findIndex(this.state, (rc) => rc._id === _id);
        this.state.splice(index, 1);
        this.refreshStatusMessage();
    }

    // Contributor

    public editContributor(contributor: Contributor) {
        this.contributor = _.merge({}, contributor);
        $('#createContributorForm').modal('show');
        this.formState = FormContributorState.editContributor;
    }

    public cancelContributor() {
        $('#createContributorForm').modal('hide');
        if (!(this as any).$refs.releaseContributor.hasEdits) {
            this.formState = FormContributorState.list;
        } else {
            this.formState = FormContributorState.editReleaseContributor;
        }
    }

    public saveContributor(contributor: Contributor) {
        this.formState = FormContributorState.editReleaseContributor;
        $('#createContributorForm').modal('hide');
        if (_.isNull(this.releaseContributor)) {
            this.releaseContributor = createDefaultValue(releaseContributorSchema);
        }
        (this as any).releaseContributor.contributor = _.merge({}, contributor);
    }

}

export default EditContributors;
