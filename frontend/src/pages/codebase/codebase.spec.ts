import EditCodebase, {schema} from './edit'
import {createDefaultValue} from 'pages/form'
import {codebaseAPI} from 'api'
import * as _ from 'lodash'

async function createCodebase() {
    const codebase = _.merge(createDefaultValue(schema), {
        title: 'Sugarscape',
        description: 'A simulation where agent compete and cooperate for sugar and spice',
        tags: [{ name: 'Python'}],
    });
    const vm = new EditCodebase();
    vm.state = codebase;
    expect(vm.state.title).toBe('Sugarscape');
    await vm.createOrUpdate();
    return vm.state.identifier;
}

describe('codebase editing', () => {
    it('should allow updating and retrieving of codebases', async () => {
        const _identifier = await createCodebase();
        try {
            console.log('foo');
            const vm = new EditCodebase({propsData: {_identifier}});
            await vm.initializeForm();
            expect((<any>vm).title).toBe('Sugarscape');

            (<any>vm).title = 'Codebase Model';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).toBe('Codebase Model');

            await codebaseAPI.delete(_identifier);
        } catch (e) {
            if (e.response) {
                console.log(e)
            }
            throw e;
        }
    })
});