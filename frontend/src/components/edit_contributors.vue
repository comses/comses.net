<template>
    <div>
        <hr>
        <label class="form-control-label">Current Contributors</label>
        <draggable :list="contributors" @start="drag=true" @end="drag=false">
            <ul v-for="(contributor, index) in contributors" :key="index" class="list-group">
                <li class="list-group-item justify-content-between" @click="updateContributor(contributor)">
                    {{ contributor.name }}
                    <span class="badge badge-default badge-pill">
                        <span class="fa fa-copy"></span>
                    </span>
                </li>
            </ul>
        </draggable>
        <small class="text-muted">Click on a contributor to edit it. Drag and drop contributors to change the order in which they appear. Main contributors at the top
        </small>
        <div class="row">
            <div class="col-md-6 col-sm-12">
                <c-input name="given_name" :value="state.given_name" @input="setGivenName">
                    <label class="form-control-label" slot="label">Given Name</label>
                </c-input>
                <c-input name="middle_name" :value="state.middle_name" @input="setMiddleName">
                    <label class="form-control-label" slot="label">Middle Name</label>
                </c-input>
                <c-input name="family_name" :value="state.family_name" @input="setFamilyName">
                    <label class="form-control-label" slot="label">Family Name</label>
                </c-input>
                <c-edit-affiliations :value="state.affiliations_list" @create="state.affiliations_list.push($event)" @remove="state.affiliations_list.splice($event, 1)" @modify="state.affiliations_list.splice($event.index, 1, $event.value)" name="affiliations" placeholder="Add affiliation">
                    <label class="form-control-label" slot="label">Affiliations</label>
                    <small class="form-text text-muted" slot="help">The institution(s) and other groups you are affiliated with</small>
                </c-edit-affiliations>
                <c-input type="select" name="type" :value="state.type" @input="setType">
                    <label class="form-control-label" slot="label">Contributor Type</label>
                </c-input>
                <c-input type="checkbox" name="is_maintainer" v-model="state.is_maintainer">
                    <label class="form-control-label" slot="label">Is Maintainer?</label>
                </c-input>
                <c-input type="checkbox" name="is_rights_holder" v-model="state.is_rights_holder">
                    <label class="form-control-label" slot="label">Is Rights Holder?</label>
                </c-input>
                <c-input name="role" v-model="state.role">
                    <label class="form-control-label" slot="label">Role</label>
                </c-input>
                <c-input name="username" v-model="state.username">
                    <label class="form-control-label" slot="label">Username</label>
                </c-input>
                <button type="button" class="btn btn-primary" @click="addContributor(state)">Add Contributor</button>
            </div>
            <div class="col-md-6 col-sm-12">
                <ul class="list-group" v-if="matchingContributors.length > 0">
                    <li v-for="matchingContributor in matchingContributors" class="list-group-item justify-content-between">
                        {{ matchingContributor.name }}
                        <span class="badge badge-default badge-pill" @click="updateContributor(matchingContributor)">
                            <span class="fa fa-copy"></span>
                        </span>
                    </li>
                </ul>
                <div v-else>No matching contributors</div>
                <small class="text-muted">Contributors matching form input. To partially autofill the form, click on the matching contributor</small>
            </div>
        </div>
        <hr>
        <!-- Releases go here -->
    </div>
</template>
<script lang="ts">
import * as Vue from 'vue'
import { Prop, Component } from 'vue-property-decorator'
import { CalendarEvent } from 'store/common'
import { api } from 'api/index'
import Datepicker from 'components/forms/datepicker.vue'
import Input from 'components/forms/input.vue'
import Markdown from 'components/forms/markdown.vue'
import MessageDisplay from 'components/message_display.vue'
import EditItems from 'components/edit_items.vue'
import Multiselect from 'vue-multiselect'
import * as draggable from 'vuedraggable'
import * as _ from 'lodash'

const listContributors = _.debounce((state, self) => api.contributors.list(state).then(data => self.matchingContributors = data.results), 800);

@Component({
    components: {
        'c-edit-affiliations': EditItems,
        'c-message-display': MessageDisplay,
        'c-input': Input,
        draggable
    }
})
class EditContributors extends Vue {
    @Prop
    contributors: Array<object>;

    matchingContributors: Array<object> = [];

    state: {
        is_maintainer: boolean
        is_rights_holder: boolean
        role: string
        affiliations_list: Array<string>
        given_name: string
        middle_name: string
        family_name: string
        type: string
    } = { is_maintainer: false, is_rights_holder: false, role: '', affiliations_list: [], given_name: '', middle_name: '', family_name: '', type: 'person' };


    searchContributors() {
        listContributors.cancel();
        listContributors(this.state, this);
    }

    setGivenName(given_name: string) {
        this.state.given_name = given_name;
        this.searchContributors();
    }

    setMiddleName(middle_name: string) {
        this.state.middle_name = middle_name;
        this.searchContributors();
    }

    setFamilyName(family_name: string) {
        this.state.family_name = family_name;
        this.searchContributors();
    }

    setType(type: string) {
        this.state.type = type;
        this.searchContributors();
    }

    addContributor(state) {
        state.name = state.given_name + ' ' + state.family_name;
        this.$emit('addContributor', state);
    }

    updateContributor(contributor) {
        this.state = contributor;
    }
}

export default EditContributors;
</script>
