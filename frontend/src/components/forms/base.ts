import * as Vue from 'vue'
import { Component, Prop } from 'vue-property-decorator'
import * as _ from 'lodash'

@Component
class BaseControl extends Vue {
    @Prop
    value;

    @Prop
    name;

    @Prop
    customId;

    @Prop({ default: () => [] })
    errorMsgs: Array<string>;

    get controlId() {
        return _.isUndefined(this.customId) ? _.uniqueId(this.name) : this.customId;
    }

    get isInvalid() {
        return this.errorMsgs.length > 0;
    }

    get errorMessage() {
        return this.errorMsgs.join(', ');
    }

    updateValue(value: any) {
        this.$emit('input', value);
    }
}

export default BaseControl;
