import EditEvent, {schema} from './edit'
import {createDefaultValue} from "pages/form"
import {eventAPI} from "api"
import * as _ from 'lodash'
import axios from 'axios'

import * as stringify from 'stringify-object'


async function createEvent() {
    const event = _.merge(createDefaultValue(schema), {
        title: 'ESSA 2007',
        location: 'Boulder, CO',
        description: 'Conference'
    });
    const vm = new EditEvent({propsData: {id: null}});
    vm.$set(vm, 'state', event);
    return vm.createOrUpdate();
}

describe('event editing', () => {
    it('should allow updating and retrieving of events', async () => {
        try {
            const response = await createEvent();
            const id = response.data.id;
            const vm = new EditEvent({propsData: {id}});
            await vm.initializeForm();
            expect((<any>vm).title).toBe('ESSA 2007');

            (<any>vm).title = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).toBe('foo');

            await eventAPI.delete(id);

        } catch (e) {
            if (e.response) {
                console.log(e.response)
            }
            throw e;
        }
    });
});