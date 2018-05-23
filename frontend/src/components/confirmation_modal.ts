import {Component, Prop} from "vue-property-decorator";
import Vue from 'vue'
import {api} from "connection";
import * as _ from 'lodash';

@Component({
    template: `<div class="modal fade" :id="modalId" tabindex="-1" role="dialog" :aria-labelledby="modalLabelId" aria-hidden="true">
        <div class="modal-dialog" role="document">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" :id="modalLabelId">{{ title }}</h5>
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
                </div>
                    <div class="modal-body">
                        <slot name="body"></slot>
                        <div class="alert alert-danger" v-for="error in errors">
                            {{ error }}
                        </div>
                    </div>
                <div class="modal-footer">
                    <div class="btn-group">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" @click="submit" v-if="ajax_submit">Save changes</button>
                        <form v-else>
                            <button type="submit" class="btn btn-primary" formmethod="post" :formaction="url">Save changes</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>`
})
export class ConfirmationModal extends Vue {
    @Prop({default: true})
    ajax_submit: boolean;

    @Prop()
    title: string;

    @Prop()
    url: string;

    @Prop()
    base_name: string;

    errors: Array<string> = [];

    get modalId() {
        return this.base_name;
    }

    get modalLabelId() {
        return `${this.base_name}Label`;
    }

    async submit() {
        try {
            const response = await api.axios.post(this.url);
            this.errors = [];
            this.$emit('success', response.data);
            (<any>$)(`#${this.modalId}`).modal('hide');
        } catch (e) {
            if (_.isArray(_.get(e, 'response.data'))) {
                this.errors = e.response.data;
            } else {
                this.$emit('error', e);
                this.errors = ['Submission failed'];
            }
        }
    }
}