import * as Vue from 'vue'
import {Store, mapGetters} from "vuex";

enum InputType {
    text,
    checkbox,
    button
}

class FormElement<T> {
    constructor(public h: Vue.CreateElement, public store: Store<T>) {}

    private lookup(key: keyof T) {
        return this.store.state[key];
    }

    formGroup(label: string, element: Vue.VNode) {
        return this.h('div', {'class': 'form-group'}, [
            this.label(label), element
        ])
    }

    input() {
        return this.h();
    }

    label(value: string) {
        return this.h('label', value);
    }

    button(label: string, value: string) {
        this.h()
    }

    text(value: string) {
        return this.h('input')
    }

    textarea(value: string) {
        return this.h('textarea', {}, value)
    }
}

function formFactory(path: string, form_elements: Array<{ name: string }>) {
    // dynamically create a form vue component for a particular part of a store
    const methods = {
        // call mutations to set store values
        // call action submit the form
    };
    const names = form_elements.map((el) => el.name);
    const computed = {
        ...mapGetters(path, names)
    };
    return Vue.extend({
        methods,
    });
}