import Vue from 'vue'
import Input from './input'

describe('input.ts', () => {
   it('should initialize correctly', () => {
       const label = 'Description';
       const vm = new Vue({
           el: document.createElement('div'),
           render: (h) => h(Input, { props: { value: 'foo', label }})
       });
       expect((<HTMLElement>vm.$el.querySelector('div label')).textContent).toBe(label);
       expect((<HTMLInputElement>vm.$el.querySelector('div input')).value).toBe('foo');
   })
});