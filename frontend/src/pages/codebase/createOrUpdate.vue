<template>
    <div>
        <c-input label="Title" :errors="errors.title" v-model="data.title"></c-input>
        <c-textarea label="Description" :errors="errors.description" rows="3" v-model="data.title"></c-textarea>
        <c-input-change label="Published?" type="checkbox"
                        :errors="errors.live" v-model="data.live"></c-input-change>
        <c-input-change label="Is a Replication?" type="checkbox"
                        :errors="errors.is_replication" v-model="data.is_replication">
        </c-input-change>
        <c-input label="DOI" :errors="errors.doi" v-model="data.doi"></c-input>
        <c-tagger v-model="data.keywords">
        </c-tagger>

        <c-input label="Repository URL" :errors="errors.repository_url" v-model="data.repository_url"></c-input>
        <c-contributors :errors="errors.contributors" v-model="data.contributors"></c-contributors>
        <div>Repository URL, Publications, References, Contributors</div>

        <div>Release DOI, License, Description, Embargo End Date, Version Number, Platforms, Programming Languages, Package Archive</div>
        <button type="button" class="btn btn-primary">Submit</button>
    </div>
</template>
<script lang="ts">
    import * as Vue from 'vue'
    import {Component} from 'vue-property-decorator'
    import Input from '../../components/forms/input.vue'
    import InputChange from '../../components/forms/input_change.vue'
    import Tagger from '../../components/tagger.vue'
    import TextArea from '../../components/forms/textarea.vue'
    import {Errors, Codebase} from '../../store/common'
    import {codebase} from '../../store/defaults'

    @Component({
        components: {
            'c-input': Input,
            'c-textarea': TextArea,
            'c-input-change': InputChange,
            'c-tagger': Tagger
        }
    })
    export default class CodebaseCreateOrUpdate extends Vue {
        data = {...codebase};
        errors: Errors<Codebase> = {
            title: ['Too short'],
            description: [],
            live: [],
            is_replication: [],
            doi: [],
            keywords: [],
            repository_url: []
        };
    }
</script>
