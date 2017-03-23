import * as Vue from 'vue'

enum InputType {
    text,
    password,
    checkbox,
    button
}

export class FormBuilder<T> {
    constructor(public h: Vue.CreateElement) {
    }

    form(children: Array<Vue.VNode>) {
        return this.h('form', {}, children);
    }

    formGroup(label: Vue.VNode, element: Vue.VNode) {
        return this.h('div', {'class': 'form-group'}, [
            label, element
        ])
    }

    input(value: string, type: InputType) {
        return this.h('input', {domProps: {type: InputType[type]}}, value);
    }

    label(value: string) {
        return this.h('label', value);
    }

    button(value: string, click): Vue.VNode {
        return this.h('label', {on: {click}}, value)
    }

    text(value: string) {
        return this.input(value, InputType.text)
    }

    textarea(value: string) {
        return this.h('textarea', {}, value)
    }

    password(value: string) {
        return this.input(value, InputType.password)
    }
}