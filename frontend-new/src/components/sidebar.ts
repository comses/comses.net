
import Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'

import Input from '@/components/forms/input'
import Datepicker from '@/components/forms/datepicker';
import {VueClass} from "vue-class-component/lib/declarations";


@Component({
    template: `<div>
        <div class="btn btn-primary w-100"><a class='text-white' href='/codebases/add/'>Submit a model</a></div>
        <div class="card-metadata">
            <div class="title">
                Search
            </div>
            <div class="card-body">
                <c-input type="text" v-model="state.keyword_search" name="keyword_search" :errorMsgs="[]">
                    <label class="form-control-label" slot="label">Keywords</label>
                </c-input>
                <c-date-picker v-model="state.start_date" name="start_date" :errorMsgs="[]" :clearButton="true">
                    <label class="form-control-label" slot="label">Published Start Date</label>
                </c-date-picker>
                <c-date-picker v-model="state.end_date" name="end_date" :errorMsgs="[]" :clearButton="true">
                    <label class="form-control-label" slot="label">Published End Date</label>
                </c-date-picker>
            </div>
        </div>
        <div class="card-metadata">
            <div class="title">
                Tags
            </div>
            <div class="card-body">
                <c-input type="text" v-model="state.tag_search" name="tag_search" :errorMsgs="[]">
                    <label class="form-control-label" slot="label">Find Tags</label>
                </c-input>
                <div>
                    <div class="my-1" v-for="tag in state.tags">
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
            <div class="card-body">
                <c-input type="text" v-model="state.author_search" name="author_search" :server_errors="[]">
                    <label class="form-control-label" slot="label">Find Authors</label>
                </c-input>
                <div>
                    <div class="my-1" v-for="author in state.authors">
                        <div :class="['btn', 'btn-sm', author.selected ? 'btn-secondary': 'btn-outline-secondary']">
                            {{ author.name }}
                        </div>
                        <span class="text-muted">x {{ author.count }}</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="btn btn-primary w-100">Search</div>
    </div>`,
    components: {
        'c-input': Input,
        'c-date-picker': Datepicker
    }
})
export default class Sidebar extends Vue {
    state = {
        keyword_search: 'foo',
        start_date: null,
        end_date: null,
        tag_search: 'bar',
        tags: [
            {name: 'ecology', selected: false, count: 52},
            {name: 'decision', selected: true, count: 10}
        ],
        author_search: 'baz',
        authors: [
            {name: 'Marco Janssen', selected: false, count: 52},
            {name: 'Michael C. Barton', selected: false, count: 43}
        ]
    };
};