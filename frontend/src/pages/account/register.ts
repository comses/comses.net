import * as Vue from 'vue'
import Component from 'vue-class-component'
import { FormBuilder } from '../../components/FormMixin'

@Component({})
class Register extends Vue {

    render(h) {
        const { form, formGroup, label, text, password } = new FormBuilder(this.$createElement);
        return form([
            formGroup(label('Username'), text('')),
            formGroup(label('Password'), password(''))
        ])
    }
}