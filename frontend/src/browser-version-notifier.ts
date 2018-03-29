import {detect} from 'detect-browser'
import Vue from 'vue'
import {Component, Prop} from 'vue-property-decorator';

@Component({
    template: `<ul class="navbar-nav ml-auto">
        <li class="nav-item" v-if="!supported">
            <div class="alert alert-warning mb-0">
                Your browser {{ browser_full_name }} is unsupported. Some site functionality may not work.
            </div>
        </li>
    </li>`
})
export class BrowserDetect extends Vue {
    @Prop()
    browser: any;

    get browser_full_name() {
        if (this.browser && this.browser.name && this.browser.version) {
            return `${this.browser.name} ${this.browser.version}`;
        }
        return 'Unknown'
    }

    get supported() {
        if (this.browser) {
            const version = parseInt(this.browser.version.split('.')[0]);
            if (this.browser.name === 'ie' && version <= 11) {
                return false;
            } else if (this.browser.name === 'chrome' && version <= 58) {
                return false;
            }
        }
        return true;
    }
}

new BrowserDetect({propsData: {browser: detect()}}).$mount('#browser-message');
