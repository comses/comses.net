import {Component, Prop} from 'vue-property-decorator'
import * as Vue from 'vue'
import * as _ from 'lodash'

@Component({
    template: `<div>
        <div v-for="m in messages" :class="m.classNames">
            {{ m.message }}
        </div>
        <div class="btn btn-danger" v-if="messages.length > 0" @click="clear">Clear Messages</div>
    </div>`
})
export default class MessageDisplay extends Vue {
    @Prop
    messages?: Array<{classNames: string, message: string}>;

    clear() {
        this.$emit('clear');
    }
}