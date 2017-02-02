// // https://journal.artfuldev.com/write-tests-for-typescript-projects-with-mocha-and-chai-in-typescript-86e053bdb2b6#.pluejbkms
// import { expect } from 'chai'
// import { mutations } from '../src/store/mutations'
// import { ActionAPI } from '../src/store/actions'
// import { initialState } from '../src/store/index'
// import {State, Job } from "../src/store/types";
// import * as api from '../src/api/index'
//
// function clone(object) {
//     return JSON.parse(JSON.stringify(object));
// }
//
// describe('Addition test', () => {
//     it('should satisfy the associative property', () => {
//        expect((1+2)+3).to.equal(1+(2+3));
//     });
// });
//
// describe('SET_JOB', () => {
//     it('should set the job detail state', () => {
//         const state: State = clone(initialState);
//         const job: Job = clone(initialState.job);
//         mutations.SET_JOB(state, job);
//         expect(state.job.detail).to.be.deep.equal(job);
//     })
// });
//
// describe('FETCH_JOB', () => {
//     it('should match the schema', () => {
//
//     })
// });