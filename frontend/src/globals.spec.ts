import { expect } from 'chai';

describe('globals', () => {
    it('__BASE_URL__ should be set', () => {
        expect(['http://localhost:8000', 'http://cms:8000', '']).to.contain((<any>window).__BASE_URL__)
    });
});