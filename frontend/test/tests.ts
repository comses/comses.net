// https://journal.artfuldev.com/write-tests-for-typescript-projects-with-mocha-and-chai-in-typescript-86e053bdb2b6#.pluejbkms
import { expect } from 'chai'

describe('Addition test', () => {
    it('should satisfy the associative property', () => {
       expect((1+2)+3).to.equal(1+(2+3));
    });
});

