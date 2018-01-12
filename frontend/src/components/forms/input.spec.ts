import Vue from 'vue'
import Input from './input'
import { expect } from 'chai'

describe('input.ts', () => {
   it('should initialize correctly', () => {
       const label = 'Description';
       const vm = new Vue({
           el: document.createElement('div'),
           render: (h) => h(Input, { props: { value: 'foo', label }})
       });
       expect((<HTMLElement>vm.$el.querySelector('div label')).textContent).to.equal(label);
       expect((<HTMLInputElement>vm.$el.querySelector('div input')).value).to.equal('foo');
   })
});