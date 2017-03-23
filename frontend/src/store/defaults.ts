import {Job, CalendarEvent, Codebase} from './common'

export const job: Job = {
    description: '',
    summary: '',
    title: '',
    tags: []
};

export const codebase: Codebase = {
    title: '',
    description: '',
    doi: null,
    live: false,
    is_replication: false,
    keywords: [],
    repository_url: '',
    contributors: []
};

export const defaultEvent: CalendarEvent = {
    description: '',
    summary: '',
    title: '',
    tags: [],
    location: '',
    early_registration_deadline: '',
    submission_deadline: '',
    start_date: '',
    end_date: ''
};