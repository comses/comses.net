import EditJob, {schema} from './edit'
import {createDefaultValue} from "pages/form"
import {JobAPI} from "api"
import * as _ from 'lodash'

const title = 'Postdoc on ABM';
const description = 'Postdoc on ABM at ASU for 2018';

async function createJob() {
    const vm = new EditJob();
    const job = _.merge(createDefaultValue(schema), {title, description});
    vm.state = job;
    await vm.createOrUpdate();
    return vm.state.id;
}

describe('jobs editing', () => {
    let api = new JobAPI();
    it('should allow updating and retrieving of jobs', async () => {
        try {
            const _id = await createJob();
            const vm = new EditJob({ propsData: {_id}});
            await vm.initializeForm();
            expect((<any>vm).title).toBe(title);

            (<any>vm).title = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).toBe('foo');

            await api.delete(_id);

        } catch (e) {
            if (e.response) {
                console.log(e.response);
            }
            throw e;
        }
    });
});
