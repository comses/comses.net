import { Prop, Component, Watch } from 'vue-property-decorator'
import * as Vue from 'vue'
import { CalendarEvent, CodebaseContributor, Contributor } from 'store/common'
import { api } from 'api/index'
import { store } from './store'
import Checkbox from 'components/forms/checkbox.vue'
import Datepicker from 'components/forms/datepicker.vue'
import Input from 'components/forms/input.vue'
import Markdown from 'components/forms/markdown.vue'
import MessageDisplay from 'components/message_display.vue'
import EditItems from 'components/edit_items.vue'
import Multiselect from 'vue-multiselect'
import * as draggable from 'vuedraggable'
import * as _ from 'lodash'

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

@Component(<any>{
    template: `<div>
        <hr>
        <label class="form-control-label">Current Contributors</label>
        <draggable v-model="releaseContributors">
            <ul v-for="releaseContributor in releaseContributors" :key="releaseContributor._id" class="list-group">
                <li class="list-group-item justify-content-between">
                    {{ releaseContributor.contributor.given_name }} {{ releaseContributor.contributor.family_name }} ({{ releaseContributor.role }})
                    <div>
                        <span class="badge badge-default badge-pill" @click="setReleaseContributor(releaseContributor)">
                            <span class="fa fa-edit"></span>
                        </span>
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
                <button class="btn btn-primary pull-right" type="button" @click="createNewReleaseContributor"><span class="fa fa-plus"></span></button>
            </div>
        </div>
        <div class="card" v-if="releaseContributor !== null">
            <div class="card-header">
                Release Contributor
            </div>
            <div class="card-block">
                <div :class="['form-group', contributorError ? 'has-danger' : '' ]">
                    <label class="form-control-label">Contributor</label>
                    <div class="row">
                        <div class="col-11">
                            <multiselect
                                v-model="releaseContributor.contributor"
                                label="name"
                                track-by="id"
                                placeholder="Type to find contributor"
                                :allow-empty="true"
                                :options="matchingContributors"
                                :multiple="false"
                                :loading="isLoadingContributors"
                                :searchable="true"
                                :internal-search="false"
                                :options-limit="50"
                                :limit="20"
                                :disabled="isNewContributor"
                                @search-change="fetchMatchingContributors">
                            </multiselect>
                        </div>
                        <div class="col-1">
                            <button type="button" class="btn btn-primary" @click="addContributor"><span class="fa fa-plus"></span></button>
                        </div>
                    </div>
                    <div class="form-control-feedback form-control-danger" v-show="contributorError">
                        {{ contributorError }}
                    </div>
                </div>
                <div v-if="isNewContributor" class="card">
                    <div class="card-header">
                        Create a contributor
                    </div>
                    <div class="card-block">
                        <div>User Search</div>
                        <c-input name="username" v-model="releaseContributor.contributor.username" label="User Name">
                        </c-input>
                        <c-input name="given_name" v-model="releaseContributor.contributor.given_name" label="Given Name">
                        </c-input>
                        <c-input name="middle_name" v-model="releaseContributor.contributor.middle_name" label="Middle Name">
                        </c-input>
                        <c-input name="family_name" v-model="releaseContributor.contributor.family_name" label="Family Name">
                        </c-input>
                        <c-edit-affiliations :value="releaseContributor.contributor.affiliations_list" vee-path=""
                            @create="releaseContributor.contributor.affiliations_list.push($event)" 
                            @remove="releaseContributor.contributor.affiliations_list.splice($event, 1)" 
                            @modify="releaseContributor.contributor.affiliations_list.splice($event.index, 1, $event.value)" name="affiliations" placeholder="Add affiliation">
                            <label class="form-control-label" slot="label">Affiliations</label>
                            <small class="form-text text-muted" slot="help">The institution(s) and other groups you are affiliated with</small>
                        </c-edit-affiliations>
                        <c-input type="select" name="type" v-model="releaseContributor.contributor.type" label="Contributor Type">
                        </c-input>
                        <button type="button" class="btn btn-primary" @click="saveContributor">Save</button>
                    </div>
                </div>
                <c-checkbox name="is_maintainer" label="Is Maintainer?" v-model="releaseContributor.is_maintainer">
                </c-checkbox>
                <c-checkbox type="checkbox" name="is_rights_holder" label="Is Rights Holder?" v-model="releaseContributor.is_rights_holder">
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
            </div>
        </div>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-edit-affiliations': EditItems,
        'c-message-display': MessageDisplay,
        'c-input': Input,
        draggable,
        Multiselect,
    }
})
class EditContributors extends Vue {
    releaseContributor: CodebaseContributor | null = null;
    isNewContributor: boolean = false;
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
    contributorError: string = '';

    get role() {
        return <any>_.find(this.roleOptions, roleOption => roleOption.value === (<any>this.releaseContributor).role);
    }

    set role(roleOption: { label: string, value: string}) {
        if (this.releaseContributor !== null) {
            this.releaseContributor.role = roleOption.value;
        }
    }

    get releaseContributors() {
        return this.$store.state.release_contributors;
    }

    set releaseContributors(value) {
        this.$store.commit('setReleaseContributors', value);
    }

    @Watch('releaseContributor.contributor')
    resetContributorError() {
        this.contributorError = '';
    }

    fetchMatchingContributors() {
        listContributors.cancel();
        if (this.releaseContributor !== null && this.releaseContributor.contributor !== null) {
            listContributors({ family_name: this.releaseContributor.contributor.family_name }, this);
        }
    }

    createNewReleaseContributor() {
        this.setReleaseContributor({
            _id: _.uniqueId(),
            is_maintainer: false,
            is_rights_holder: false,
            role: '',
            contributor: null,
        });
    }

    setReleaseContributor(releaseContributor) {
        return this.releaseContributor = _.extend({}, releaseContributor);
    }

    addContributor() {
        if (this.releaseContributor !== null) {
            this.releaseContributor.contributor = {
                affiliations_list: [],
                given_name: '',
                middle_name: '',
                family_name: '',
                type: 'person',
                user: null,
            };
            this.isNewContributor = true;
        }
    }

    cancelContributor() {

    }

    cancelReleaseContributor() {
        this.releaseContributor = null;
    }

    saveContributor() {
        this.isNewContributor = false;
    }

    saveReleaseContributor() {
        // TODO: validation check here to prevent saving bad
        if ((<any>this.releaseContributor).contributor !== null) {
            this.$store.commit('upsertReleaseContributor', this.releaseContributor);
            this.releaseContributor = null;
        } else {
            this.contributorError = 'Contributor must be set in order to save'
        }
    }

    deleteReleaseContributor(_id: string) {
        this.$store.commit('deleteReleaseContributor', _id);
    }
}

export default EditContributors;