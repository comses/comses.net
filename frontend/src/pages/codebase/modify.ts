import * as Vue from 'vue'
import Component from 'vue-class-component'
import {api} from "../../store/index";
import {Codebase} from "../../store/common";
import 'components/ClassComponentsHooks'

enum InputType {
    text,
    textarea,
    checkbox,
    button
}

function loadState(route) {

}

@Component({
    watch: {
        '$route': function(val) {
            console.log(val);
        }
    }
})
export default class DraftCode extends Vue {
    get draft(): Codebase {
        return this.$store.state.codebases.modify;
    }

    createFormGroup(data, label: string, type: InputType) {
        const h = this.$createElement;
        return h('div', {'class': 'form-group'}, [
            h('label', label),
            h('input', {'class': 'form-control', domProps: {type: InputType[type]}}, data)
        ]);
    }

    //
    created() {
        console.log('created');
    }

    // can't use beforeRouteLeave because it doesn't fire if we change to updating a different codebase

    logInput(event) {
        console.log(event)
    }

    render(h) {
        const {title, description, live, is_replication, doi, keywords} = this.draft;

        return h('form', {on: {input: this.logInput}}, [
            this.createFormGroup(title, 'Title', InputType.text),
            this.createFormGroup(description, 'Description', InputType.text),
            this.createFormGroup(live, 'Published?', InputType.checkbox),
            this.createFormGroup(is_replication, 'Is a replication?', InputType.checkbox),
            this.createFormGroup(doi, 'DOI', InputType.text),
            h('button', {'class': 'btn btn-primary', domProps: {type: InputType.button}}, 'Submit'),
        ])
    }


    save() {

    }
}