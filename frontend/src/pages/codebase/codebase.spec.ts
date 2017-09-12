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
    return codebaseAPI.create(codebase);
}

describe('codebase editing', () => {
    it('should allow updating and retrieving of codebases', async () => {
        try {
            const response = await createCodebase();
            const identifier = response.data.identifier;
            const vm = new EditCodebase({propsData: {identifier}});
            await vm.initializeForm();
            expect((<any>vm).title).toBe('Sugarscape');

            (<any>vm).title = 'Codebase Model';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).toBe('Codebase Model');

            await codebaseAPI.delete(identifier);
        } catch (e) {
            if (e.response) {
                console.log(e.response)
            }
            throw e;
        }
    })
});