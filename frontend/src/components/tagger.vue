<template>
    <multiselect
            :value="value"
            @input="updateValue"
            label="name"
            track-by="name"
            placeholder="Type to find keywords"
            :options="matchingTags"
            :multiple="true"
            :loading="isLoading"
            :searchable="true"
            :internal-search="false"
            :clear-on-select="false"
            :close-on-select="false"
            :options-limit="50"
            :limit="6"
            @search-change="fetchMatchingTags">
    </multiselect>
</template>
<script lang="ts">
    import * as Vue from 'vue'
    import {Component, Prop} from 'vue-property-decorator'

    import * as queryString from 'query-string'
    import {api as axios} from '../api/index'

    import Multiselect from 'vue-multiselect'

    @Component({
        components: {
            Multiselect
        }
    })
    export default class Tagger extends Vue {
        @Prop
        value: Array<{name: string}>;

        @Prop
        errors: Array<string>;

        isLoading = false;
        matchingTags = [];

        fetchMatchingTags(query) {
            this.isLoading = true;
            axios.get('/tags/?' + queryString.stringify({query, page: 1}))
                    .then(response => {
                        this.matchingTags = response.data.results;
                        this.isLoading = false;
                    })
                    .catch(response => {
                        this.$emit('error', response.data);
                        this.isLoading = false;
                    });
        }

        updateValue(value) {
            this.$emit('input', value);
        }
    }
</script>
