import {Component, Prop} from "vue-property-decorator";
import Vue from "vue";

@Component({
    template: `<div>
        <h5>Latest Events</h5>
        <div class="alert alert-danger" v-for="error in errors">
            {{ error }}
        </div>
        <div v-for="event in events">
            <div class="card">
                <div class="card-body">
                    <p><b>{{ event.date_created }}</b></p>
                    <p class="card-text">{{ event.message }}</p>
                </div>
            </div>
        </div>
    </div>`
})
export class EventLog extends Vue {
    @Prop()
    events: Array<object>;

    @Prop()
    errors: Array<string>;
}