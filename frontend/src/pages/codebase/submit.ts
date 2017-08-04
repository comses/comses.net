import { Component, Watch } from 'vue-property-decorator'
import * as Vue from 'vue'
import Checkbox from 'components/forms/checkbox.vue'
import Multiselect from 'vue-multiselect'
import Input from 'components/forms/input.vue'
import { exposeComputed } from './store'
import * as yup from 'yup'

@Component({
    template: `<div>
            <button class="btn btn-primary" type="button" @click="submit">Submit</button>
            <div class="alert alert-danger" role="alert" v-if="validationMsg.type == 'error'">
                {{ validationMsg.msg }}
            </div>
            <div class="alert alert-success" role="alert" v-if="validationMsg.type == 'success'">
                {{ validationMsg.msg }}
            </div>
        </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-input': Input,
        Multiselect,
    }
})
export default class Submit extends Vue {
    validationMsg: { type: 'error' | 'success' | 'none', msg: string} = { type: 'none', msg: ''};

    @Watch('acceptTermsAndConditions')
    onChangeAcceptTermsAndConditions() {
        this.validationMsg = { type: 'none', msg: ''};
    }

    submit() {
        this.$store.dispatch('submitIfValid')
            .then(response => this.validationMsg = { type: 'success', msg: 'Submission Successful'})
            .catch(response => this.validationMsg = { type: 'error', msg: 'Submission Failed' });
    }
}
