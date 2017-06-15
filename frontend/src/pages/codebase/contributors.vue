<template>
    <div>
        <h1>Edit Contributors</h1>
        <c-edit-contributors></c-edit-contributors>
    </div>
</template>
<script lang="ts">
    import * as Vue from 'vue'
    import { Component, Prop } from 'vue-property-decorator'

    import EditContributors from 'components/edit_contributors.vue'
    import {Contributor} from 'store/common'

    @Component({
        'c-edit-contributors': EditContributors
    })
    export default class Contributors extends Vue {
        @Prop
        contributors: Array<Contributor>;
    }
</script>
