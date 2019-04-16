import Vue from 'vue';
import Input from './input';
import { expect } from 'chai';

describe('input.ts', () => {
   it('should initialize correctly', () => {
       const label = 'Description';
       const vm = new Vue({
           el: document.createElement('div'),
           render: (h) => h(Input, { props: { value: 'foo', label }}),
       });
       expect((vm.$el.querySelector('div label') as HTMLElement).textContent).to.equal(label);
       expect((vm.$el.querySelector('div input') as HTMLInputElement).value).to.equal('foo');
   });
});
