import { Component, Watch } from 'vue-property-decorator'
import * as Vue from 'vue'
import Checkbox from 'components/forms/checkbox.vue'
import Multiselect from 'vue-multiselect'
import Input from 'components/forms/input.vue'
import { exposeComputed } from './store'
import * as yup from 'yup'

@Component({
    template: `<div>
            <c-checkbox v-model="acceptTermsAndConditions" label="Do you accept terms and conditions of archiving your model at CoMSES?">
                <template slot="label" scope="props">
                    {{ props.label }}
                </template>
            </c-checkbox>
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
    acceptTermsAndConditions: boolean = false;
    validationMsg: { type: 'error' | 'success' | 'none', msg: string} = { type: 'none', msg: ''};

    @Watch('acceptTermsAndConditions')
    onChangeAcceptTermsAndConditions() {
        this.validationMsg = { type: 'none', msg: ''};
    }

    test() {
        const schema = yup.object().shape({
            name: yup.string().required(),
            age: yup.string().required()
        })
        schema.validate({ name: ''}, {abortEarly: false}, function(err, value) {
            console.log({schema, err, value});
        })
    }

    submit() {
        this.test();
        if (this.acceptTermsAndConditions) {
            this.$store.dispatch('submit')
                .then(response => this.validationMsg = { type: 'success', msg: 'Submission Successful'})
                .catch(response => this.validationMsg = { type: 'error', msg: 'Submission Failed' });
        } else {
            this.validationMsg = {type: 'error', msg: 'In order to submit a model you must accept the terms and conditions'}
        }
    }
}
