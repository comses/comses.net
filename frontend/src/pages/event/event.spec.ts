import EditEvent from './edit'
import * as Vue from 'vue'
import * as VeeValidate from 'vee-validate'
import axios from "axios"
// import * as stringify from 'stringify-object'

Vue.use(VeeValidate);

describe('event editing', () => {
   it('should create an event', async () => {
       const event = {

       };
       const data = await axios.get('http://localhost:8000/events/1/', { headers: { 'Content-Type': 'application/json'}})
           .then(r => r.data)
           .catch(e => Promise.reject(e));
       expect((<any>data).title).toBe('ESSA 2007');
   });
});