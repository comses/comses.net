import EditJob, {schema} from './edit'
import {createDefaultValue} from "pages/form"
import {jobAPI} from "api"
import * as _ from 'lodash'

const title = 'Postdoc on ABM';
const description = 'Postdoc on ABM at ASU for 2018';

async function createJob() {
    const job = _.merge(createDefaultValue(schema), {title, description});
    const vm = new EditJob({propsData: {id: null}});
    vm.$set(vm, 'state', job);
    return vm.createOrUpdate();
}

describe('jobs editing', () => {
    it('should allow updating and retrieving of jobs', async () => {
        try {
            const response = await createJob();
            const id = response.data.id;
            const vm = new EditJob({propsData: {id}});
            await vm.initializeForm();
            expect((<any>vm).title).toBe(title);

            (<any>vm).title = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).toBe('foo');

            await jobAPI.delete(id);

        } catch (e) {
            if (e.response) {
                console.log(e.response);
            }
            throw e;
        }
    });
});