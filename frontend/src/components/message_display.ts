import {Component, Prop} from 'vue-property-decorator'
import Vue from 'vue'
import * as _ from 'lodash'
import {StatusMessages} from "store/common";

@Component({
    template: `<div class="card border-light" v-if="messages && messages.length > 0">
        <button type="button" class="close" data-dismiss="alert" aria-label="Close" @click="clear">
            <span aria-hidden="true" class="pull-right"><span class="fa fa-times"></span></span>
        </button>
        <div class="card-body px-0 py-0">
            <div v-for="m in messages" :class="m.classNames">
                {{ m.message }}
            </div>        
        </div>
    </div>`
})
export default class MessageDisplay extends Vue {
    @Prop()
    messages?: Array<{classNames: string, message: string}>;

    clear() {
        this.$emit('clear');
    }
}
