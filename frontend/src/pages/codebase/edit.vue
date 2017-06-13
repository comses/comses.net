<template>
    <div>
        <c-input v-model="state.title" name="title" :server_errors="serverErrors('title')" validate="required" @clear="clearField">
            <label class="form-control-label" slot="label">Title</label>
            <small class="form-text text-muted" slot="help">A short title describing the codebase</small>
        </c-input>
        <c-textarea name="description" :server_errors="serverErrors('title')" validate="required" @clear="clearField" rows="3" v-model="state.description">
            <label class="form-control-label" slot="label">Description</label>
        </c-textarea>
    
        <c-input name="live" :server_errors="serverErrors('live')" @clear="clearField" type="checkbox" v-model="state.live">
            <label class="form-control-label" slot="label">Published?</label>
            <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you</small>
        </c-input>
        <c-input name="replication" :server_errors="serverErrors('replication')" @clear="clearField" type="checkbox" v-model="state.is_replication">
            <label class="form-control-label" slot="label">Is a replication?</label>
        </c-input>
        <c-input name="doi" :server_errors="serverErrors('doi')" @clear="clearField" v-model="state.doi">
            <label class="form-control-label" slot="label">DOI</label>
            <small class="form-text text-muted" slot="help">A Digital Object Identifier (DOIs) for the whole codebase (all versions). DOIs make it easier for others to find and reference your code.
            </small>
        </c-input>
        <c-tagger v-model="state.tags" name="tags" :server_errors="serverErrors('tags')" @clear="clearField">
        </c-tagger>
    
        <c-input name="repository_url" :server_errors="serverErrors('repository_url')" @clear="clearField" v-model="state.repository_url">
            <label class="form-control-label" slot="label">Repository URL</label>
            <small class="form-text text-muted" slot="help">A link to the source repository (on GitHub, BitBucket etcetera). A source repository makes it easier for others collaberate with you on model development.
            </small>
        </c-input>
    
        <c-edit-contributors @addContributor="state.all_contributors.push($event)" :contributors="state.all_contributors"></c-edit-contributors>
        <div>Repository URL, Publications, References, Contributors</div>
    
        <c-edit-codebase-releases :codebase_identifier="state.identifier" :codebase_releases="state.releases"></c-edit-codebase-releases>

        <div>Release DOI, License, Description, Embargo End Date, Version Number, Platforms, Programming Languages, Package Archive</div>
        <button type="button" class="btn btn-primary">Submit</button>
    </div>
</template>
<script lang="ts">
import * as Vue from 'vue'
import { Component } from 'vue-property-decorator'
import EditContributors from '../../components/edit_contributors.vue'
import EditCodebaseReleases from '../../components/edit_codebase_releases.vue'
import Input from '../../components/forms/input.vue'
import InputChange from '../../components/forms/input_change.vue'
import Tagger from '../../components/tagger.vue'
import TextArea from '../../components/forms/textarea.vue'
import { Codebase } from '../../store/common'
import { api } from '../../api/index'

@Component({
    components: {
        'c-edit-codebase-releases': EditCodebaseReleases,
        'c-edit-contributors': EditContributors,
        'c-input': Input,
        'c-textarea': TextArea,
        'c-input-change': InputChange,
        'c-tagger': Tagger,
    }
})
export default class CodebaseCreateOrUpdate extends Vue {
    state: Codebase = {
        associatiated_publications_text: '',
        all_contributors: [],
        description: '',
        doi: null,
        featured: false,
        first_published_on: '',
        has_published_changes: false,
        identifier: '',
        is_replication: false,
        keywords: [],
        last_published_on: '',
        latest_version: null,
        live: false,
        peer_reviewed: false,
        references_text: '',
        relationships: {},
        repository_url: '',
        submitter: {
            given_name: '',
            family_name: '',
            username: ''
        },
        summary: '',
        tags: [],
        title: ''
    };

    clearField(field_name: string) {
        let self: any = this;
        self.errors.remove(field_name, 'server-side');
    }

    matchUpdateUrl(pathname) {
        let match = pathname.match(/\/codebases\/([0-9a-zA-Z_\-]+)\/update\//);
        if (match !== null) {
            match = match[1];
        }
        return match
    }

    initializeForm() {
        let id = this.matchUpdateUrl(document.location.pathname);
        if (id !== null) {
            this.retrieve(id);
        }
    }

    created() {
        this.initializeForm();
    }

    serverErrors(field_name: string) {
        let self: any = this;
        return self.errors.collect(field_name, 'server-side');
    }

    createOrUpdate() {
        if (this.state.id !== undefined) {
            this.update(this.state.identifier);
        } else {
            this.create();
        }
    }

    retrieve(identifier: string) {
        api.codebases.retrieve(identifier).then(state => this.state = state);
    }

    createMainServerError(err) {
        let self: any = this;
        self.errors.add('non_field_errors', err, 'server-side', 'server-side');
    }

    createServerErrors(err: any) {
        console.log({ serverErrors: true, err });
        let self: any = this;
        if (err.hasOwnProperty('non_field_errors')) {
            this.createMainServerError((<any>err).non_field_errors);
            delete err.non_field_errors;
        }
        for (const field_name in err) {
            self.errors.add(field_name, err[field_name], 'server-side', 'server-side');
        }
    }

    create() {
        (this as any).errors.clear('server-side');
        api.codebases.create(this.state).then(drf_response => {
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

    update(identifier: string) {
        (this as any).errors.clear('server-side');
        api.codebases.update(identifier, this.state).then(drf_response => {
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
