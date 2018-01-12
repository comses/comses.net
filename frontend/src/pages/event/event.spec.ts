import EditEvent, {schema} from './edit'
import {createDefaultValue} from "pages/form"
import * as _ from 'lodash'
import { expect } from 'chai'

import * as stringify from 'stringify-object'
import {EventAPI} from "api/index";

async function createEvent() {
    const event = _.merge(createDefaultValue(schema), {
        title: 'ESSA 2007',
        location: 'Boulder, CO',
        description: 'Conference'
    });
    const vm = new EditEvent();
    vm.state = event;
    await vm.createOrUpdate();
    return vm.state.id;
}

describe('event editing', () => {
    let api = new EventAPI();
    it('should allow updating and retrieving of events', async () => {
        try {
            const _id = await createEvent();
            const vm = new EditEvent({ propsData: {_id}});
            await vm.initializeForm();
            expect((<any>vm).title).to.equal('ESSA 2007');

            (<any>vm).title = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).to.equal('foo');

            await api.delete(_id);

        } catch (e) {
            if (e.response) {
                console.log(e.response)
            }
            throw e;
        }
    });
});
