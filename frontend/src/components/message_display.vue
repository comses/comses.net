<template>
    <div>
        <div v-for="message in display_messages" :class="classNames">
            {{ message }}
        </div>
    </div>
</template>
<script lang="ts">
    import {Component, Prop} from 'vue-property-decorator'
    import * as Vue from 'vue'
    import * as _ from 'lodash'

    @Component
    export default class MessageDisplay extends Vue {
        @Prop
        messages?: Array<string>;

        @Prop
        classNames: Array<string>;

        get display_messages() {
            return _.flatten(this.messages || []);
        }
    }
</script>
