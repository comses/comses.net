import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import * as _ from 'lodash'

@Component({
    template: `<div>
        <div v-for="message in display_messages" :class="classNames">
            {{ message }}
        </div>
    </div>`
})
export default class MessageDisplay extends Vue {
    @Prop
    messages?: Array<string>;

    @Prop
    classNames: Array<string>;

    get display_messages() {
        return _.flatten(this.messages || []);
    }
}