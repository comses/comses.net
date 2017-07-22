import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import Checkbox from 'components/forms/checkbox.vue'
import Multiselect from 'vue-multiselect'
import Input from 'components/forms/input.vue'
import { exposeComputed } from './store'

@Component({
    template: `<div>
        <div>
            <c-checkbox name="live" v-model="live" label="Published?">
                <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you</small>
            </c-checkbox>
            <multiselect v-model="licence" label="name" track-by="name" placeholder="Type to find license" :options="licenseOptions">
                <template slot="option" scope="props">
                    <div>
                        <a :href="props.option.url">{{ props.option.name }}</a>
                    </div>
                </template>
            </multiselect>
            <small class="form-text text-muted">A software licence is a document governing use and redistribution of your model</small>
        </div>
    </div>`,
    components: {
        'c-checkbox': Checkbox,
        'c-input': Input,
        Multiselect,
    },
    computed: <any>exposeComputed(['licence', 'live'])
})
export default class Permissions extends Vue {
    licenseOptions: Array<{ name: string, url: string }> = [
        { name: 'Library GPL', url: 'https://opensource.org/licenses/lgpl-license' },
        { name: 'GPL V2', url: 'https://opensource.org/licenses/gpl-license' },
        { name: 'GPL V3', url: 'https://opensource.org/licenses/gpl-license' },
        { name: 'MIT', url: 'https://opensource.org/licenses/MIT' },
        { name: 'Apache 2.0', url: 'https://opensource.org/licenses/Apache-2.0' },
        { name: 'BSD 3-Clause', url: 'https://opensource.org/licenses/BSD-3-Clause' },
        { name: 'BSD 2-Clause', url: 'https://opensource.org/licenses/BSD-2-Clause' }
    ];
}
