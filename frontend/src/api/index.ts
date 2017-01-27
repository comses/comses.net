import axios from 'axios'

export const api = axios.create({
    auth: {
        username: 'calvin',
        password: 'test'
    }
});


