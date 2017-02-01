import * as Vue from 'vue'
import { mapGetters } from 'vuex'
import Component from 'vue-class-component'
import * as _ from 'lodash'

@Component({})
export class ResourceDetail extends Vue {

    get detail() {
        return this.$store.state.resources;
    }

    renderBody() {
        return this.detail.body.map((el) => {
            switch (el.type) {
                case 'image':
                    return this.$createElement('img', {domProps: el.value});
                case 'paragraph': {
                    // this is only safe because html is sanitized server side
                    return this.$createElement('div', {domProps: {innerHTML: el.value}});
                }
                default:
                    throw new Error('invalid tag type: ' + el.type);
            }
        })
    }

    render(h) {
        return h('div', {}, this.renderBody());
    }
}