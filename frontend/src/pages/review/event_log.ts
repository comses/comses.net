import {Component, Prop} from 'vue-property-decorator';
import Vue from 'vue';

@Component({
    template: `<div>
        <h5>Latest Events</h5>
        <div class="alert alert-danger" v-for="error in errors">
            {{ error }}
        </div>
        <div v-for="event in events">
            <div class="card">
                <div class="card-body">
                    <h5 class='card-title'>{{ event.date_created }}</h5>
                    <p class="card-text">
                        <span class='badge badge-primary'>{{event.action}}</span>
                        {{ event.message }} (<em>by:</em> <a :href="event.author.absolute_url">{{event.author.name}}</a>)
                    </p>
                </div>
            </div>
        </div>
    </div>`,
})
export class EventLog extends Vue {
    @Prop()
    public events: object[];

    @Prop()
    public errors: string[];
}
