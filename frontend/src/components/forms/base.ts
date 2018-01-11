import Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator'
import * as _ from 'lodash'

@Component
export default class BaseControl extends Vue {
    @Prop({default: true})
    required;

    @Prop()
    value;

    @Prop()
    name: string;

    @Prop()
    customId;

    @Prop({default: () => []})
    errorMsgs: Array<string>;

    get requiredClass() {
        return {'required': this.required};
    }

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
