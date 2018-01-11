

describe('globals', () => {
    it('__BASE_URL__ should be set', () => {
        expect(['http://localhost:8000', 'http://cms:8000']).toContain((<any>window).__BASE_URL__)
    });
});