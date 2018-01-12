import EditCodebase, {schema} from './edit'
import {createDefaultValue} from 'pages/form'
import {CodebaseAPI} from 'api'
import * as _ from 'lodash'
import { expect } from 'chai'

async function createCodebase() {
    const codebase = _.merge(createDefaultValue(schema), {
        title: 'Sugarscape',
        description: 'A simulation where agent compete and cooperate for sugar and spice',
        tags: [{ name: 'Python'}],
    });
    const vm = new EditCodebase();
    vm.state = codebase;
    expect(vm.state.title).to.equal('Sugarscape');
    await vm.createOrUpdate();
    return vm.state.identifier;
}

describe('codebase editing', () => {
    let api = new CodebaseAPI();
    it('should allow updating and retrieving of codebases', async () => {
        const _identifier = await createCodebase();
        try {
            console.log('foo');
            const vm = new EditCodebase({propsData: {_identifier}});
            await vm.initializeForm();
            expect((<any>vm).title).to.equal('Sugarscape');

            (<any>vm).title = 'Codebase Model';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).title).to.equal('Codebase Model');

            await api.delete(_identifier);
        } catch (e) {
            if (e.response) {
                console.log(e)
            }
            throw e;
        }
    })
});
