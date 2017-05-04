<template>
    <div>
        <div class="btn btn-primary w-100">Submit a model</div>
        <div class="card-metadata">
            <div class="title">
                Search
            </div>
            <div class="card-block">
                <c-input type="text" v-model="state.content.keyword_search">
                    <label class="form-control-label" slot="label">Keywords</label>
                </c-input>
                <c-date-picker v-model="state.content.start_date" :clearButton="true">
                    <label class="form-control-label" slot="label">Published Start Date</label>
                </c-date-picker>
                <c-date-picker v-model="state.content.end_date" :clearButton="true">
                    <label class="form-control-label" slot="label">Published End Date</label>
                </c-date-picker>
            </div>
        </div>
        <div class="card-metadata">
            <div class="title">
                Tags
            </div>
            <div class="card-block">
                <c-input type="text" v-model="state.content.tag_search">
                    <label class="form-control-label" slot="label">Find Tags</label>
                </c-input>
                <div>
                    <div class="my-1" v-for="tag in state.content.tags.value">
                        <div :class="['btn', 'btn-sm', tag.selected ? 'btn-secondary': 'btn-outline-secondary']">
                            {{ tag.name }}
                        </div>
                        <span class="text-muted">x {{ tag.count }}</span>
                    </div>
                </div>
                <!-- TagList Here -->
            </div>
        </div>
        <div class="card-metadata">
            <div class="title">
                Authors
            </div>
            <div class="card-block">
                <c-input type="text" v-model="state.content.author_search">
                    <label class="form-control-label" slot="label">Find Authors</label>
                </c-input>
                <div>
                    <div class="my-1" v-for="author in state.content.authors.value">
                        <div :class="['btn', 'btn-sm', author.selected ? 'btn-secondary': 'btn-outline-secondary']">
                            {{ author.name }}
                        </div>
                        <span class="text-muted">x {{ author.count }}</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="btn btn-primary w-100">Search</div>
    </div>
</template>
<script lang="ts">
    import * as Vue from 'vue'
    import {Component, Prop} from 'vue-property-decorator'

    import Input from 'components/forms/input.vue'
    import Datepicker from 'components/forms/datepicker.vue';
    import {basePageMixin} from 'components/base_page';
    import {api as axios} from '../api/index'
    import * as queryString from 'query-string'

    @Component({
        components: {
            'c-input': Input,
            'c-date-picker': Datepicker
        },
        mixins: [basePageMixin]
    })
    export default class Sidebar extends Vue {
        state = {
            content: {
                keyword_search: {value: 'foo', errors: []},
                start_date: {value: null, errors: []},
                end_date: {value: null, errors: []},
                tag_search: {value: 'bar', errors: []},
                tags: {
                    value: [
                        {name: 'ecology', selected: false, count: 52},
                        {name: 'decision', selected: true, count: 10}
                    ],
                    errors: []
                },
                author_search: {value: 'baz', errors: []},
                authors: {
                    value: [
                        {name: 'Marco Janssen', selected: false, count: 52},
                        {name: 'Michael C. Barton', selected: false, count: 43}
                    ]
                }
            }
        };
    }
</script>
