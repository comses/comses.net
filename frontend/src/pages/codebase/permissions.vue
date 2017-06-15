<template>
    <div>
        <h1>Permissions</h1>
        <div>
            <c-input name="live" :server_errors="serverErrors('live')" @clear="clearField" type="checkbox" v-model="permissions.live">
                <label class="form-control-label" slot="label">Published?</label>
                <small class="form-text text-muted" slot="help">Published models are visible to everyone. Unpublished models are visible only to you</small>
            </c-input>
            <multiselect :value="permissions.license" @input="updateLicense" label="license" track-by="name" placeholder="Type to find license" :options="license_options">
                <template slot="option" scope="props">
                    <div>
                        <a href="props.option.url">{{ props.option.name }}</a>
                    </div>
                </template>
            </multiselect>
        </div>
    </div>
</template>
<script lang="ts">
import { Component, Prop } from 'vue-property-decorator'
import * as Vue from 'vue'
import Multiselect from 'vue-multiselect'
import Input from 'components/forms/input.vue'

@Component({
    components: {
        'c-input': Input,
        Multiselect,
    }
})
export default class Permissions extends Vue {
    @Prop
    permissions: { license: string, live: boolean };

    licenseOptions: Array<{ name: string, url: string }> = [
        { name: 'Library GPL', url: 'https://opensource.org/licenses/lgpl-license' },
        { name: 'GPL V2', url: 'https://opensource.org/licenses/gpl-license' },
        { name: 'GPL V3', url: 'https://opensource.org/licenses/gpl-license' },
        { name: 'MIT', url: 'https://opensource.org/licenses/MIT' },
        { name: 'Apache 2.0', url: 'https://opensource.org/licenses/Apache-2.0' },
        { name: 'BSD 3-Clause', url: 'https://opensource.org/licenses/BSD-3-Clause' },
        { name: 'BSD 2-Clause', url: 'https://opensource.org/licenses/BSD-2-Clause' }
    ];

    updateLicense(licenseOption: { name: string, url: string}) {
        this.$emit('updateLicense', licenseOption.name);
    }
}
</script>
