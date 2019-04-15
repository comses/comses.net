import EditProfile, {schema} from './edit'
import { expect } from 'chai'
import {__TEST_USER_ID__} from "../../__config__/common";

describe('profile editing', () => {
    it('should allow updates', async () => {
        try {
            const vm = new EditProfile({ propsData: { _pk: __TEST_USER_ID__}});
            await vm.initializeForm();
            expect((<any>vm).given_name).to.equal('Test');
            expect((<any>vm).email).to.equal('a@b.com');

            (<any>vm).given_name = 'foo';
            await vm.createOrUpdate();
            await vm.initializeForm();
            expect((<any>vm).given_name).to.equal('foo');

            (<any>vm).state.given_name = 'Test';
            await vm.createOrUpdate();
        } catch(e) {
            if (e.response) {
                console.log(e.response);
            }
            throw e;
        }
    });
});
