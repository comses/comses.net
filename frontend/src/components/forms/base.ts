import * as Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'
import * as _ from 'lodash'

@Component
class BaseControl extends Vue {
    @Prop
    value;

    @Prop
    name;

    @Prop
    server_errors: Array<string>;

    get hasDanger() {
        let self: any = this;
        return (this.server_errors !== undefined && this.server_errors.length > 0) || self.errors.any();
    }

    get errorMessage() {
        let self: any = this;
        return _.concat(this.server_errors || [], self.errors.all()).join(', ');
    }

    updateValue(value: string) {
        let self: any = this;
        self.errors.remove(this.name, 'ajax');
        this.$emit('input', value);
        this.$emit('clear', this.name);
    }
}

export default BaseControl;