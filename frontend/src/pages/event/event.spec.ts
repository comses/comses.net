import EditEvent, {schema} from './edit'
import {createDefaultValue} from "pages/form"
import * as _ from 'lodash'
import { expect } from 'chai'

import * as stringify from 'stringify-object'
import {EventAPI} from "api/index";

function addDaysToDate(date: Date, days: number): Date {
    const newDate = new Date(date.valueOf());
    newDate.setDate(newDate.getDate() + days);
    return newDate;
}

async function createEvent() {
    const seed_date = new Date();
    const early_registration_date = addDaysToDate(seed_date, 1);
    const registration_date = addDaysToDate(early_registration_date, 2);
    const start_date = addDaysToDate(registration_date, 3);
    const event = _.merge(createDefaultValue(schema), {
        title: 'ESSA 2007',
        location: 'Boulder, CO',
        description: 'Conference',
        early_registration_date: early_registration_date.toISOString(),
        registration_date: registration_date.toISOString(),
        start_date: start_date.toISOString()
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
