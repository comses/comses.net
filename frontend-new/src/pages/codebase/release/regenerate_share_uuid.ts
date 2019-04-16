import Vue from 'vue';
import {Component, Prop} from 'vue-property-decorator';
import {api} from '@/api/connection';

@Component({})
class RegenerateShareUUID extends Vue {
    @Prop()
    public absolute_url: string;

    @Prop()
    public initial_share_url: string;

    public share_url: string = '';

    public handle;

    public created() {
        this.share_url = this.initial_share_url;
    }

    public regenerateShareUuid() {
        api.axios.post(`${this.absolute_url}regenerate_share_uuid/`)
            .then((r) => this.share_url = r.data);
    }
}

const el = document.getElementById('regenerate_share_uuid');
if (el) {
    const initial_share_url = el.getAttribute('data-share-url');
    const absolute_url = el.getAttribute('data-absolute-url');
    new RegenerateShareUUID({propsData: {initial_share_url, absolute_url}})
        .$mount(el);
}
