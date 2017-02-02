import * as Vue from 'vue'
import Component from 'vue-class-component'
import {mapGetters, Store} from "vuex";
import  { Job } from '../../store/common'
import { api } from '../../store/index'

@Component({
    template: `
        <div>
            <h2>Create a new job</h2>
            <form>
                <div class="form-group">
                    <label>Title</label>
                    <input type="text" class="form-control" placeholder="Enter Title" :value="title" @input="setTitle">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea class="form-control" :value="description" @input="setDescription"></textarea>
                </div>
                <button type="button" class="btn btn-primary" @click="create">Submit</button>
            </form>
        </div>`
})
class JobCreate extends Vue implements Job {
    // determine whether you are creating or updating based on wat route you are on
    // update -> grab the appropriate state from the store
    // create -> use the default store state

    description = '';
    title = '';

    setTitle(event) {
        this.title = event.target.value;
    }

    setDescription(event) {
        // this.description = event.target.value;
        this.$store.commit({type: 'job/draft/setDescription', data: event.target.value});
    }

    create() {
        this.$store.dispatch(api.job.actions.modify({
            description: this.description,
            title: this.title,

        }));
        this.$router.go(-1);
    }
}

export default JobCreate;