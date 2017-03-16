<template>
    <form class="form-group row" action="url" method="get"
          enctype="application/x-www-form-urlencoded">
        <div class="col-12">
            <input type="text" class="form-control" name="query" placeholder="Search" v-model="data.query">
        </div>
        <div class="col-12">
            <c-tagger v-model='data.tags' v-on:errors='setTagErrors'>
            </c-tagger>
            <small class="form-text text-muted">Filter by all the selected tags (all tags must be matched, not just
                one)
            </small>
        </div>
        <div class="col-12">
            <button class="btn btn-primary" type="button" @click="submitSearch">Search</button>
            <a class="btn btn-primary pull-right" :href="createUrl">Create {{ model_name }}</a>
        </div>
    </form>
</template>
<script lang="ts">
    import {searchSchemaValidate} from 'store/schema/index';
    import * as Vue from 'vue'
    import {Component, Prop} from 'vue-property-decorator'
    import {Errors, Search} from 'store/common'
    import * as queryString from 'query-string'
    import * as Ajv from 'ajv'

    import Tagger from 'components/tagger.vue'


    @Component({
        components: {
            'c-tagger': Tagger
        },
        computed: {
            createUrl() {
                return window.location.pathname + 'create/'
            }
        }
    })
    class SearchForm extends Vue {
        @Prop
        model_name: string;

        data: Search = {query: '', tags: []};

        created() {
            const qs = queryString.parse(window.location.search);
            const valid = searchSchemaValidate(qs);
            if (!valid) {
                console.error(searchSchemaValidate.errors);
            }

            const tags = qs.tags.map(t => {
                return {name: t}
            });
            this.data = {query: qs.query, tags};
        }

        errors: Errors<Search>;

        setTagErrors(tag_errors) {
            this.errors.tags = tag_errors;
        }

        submitSearch() {
            const tags = this.data.tags.map(t => t.name);
            const data = {query: this.data.query, tags};
            const q = queryString.stringify(data);
            window.location.search = q;
        }
    }
    export default SearchForm;
</script>
