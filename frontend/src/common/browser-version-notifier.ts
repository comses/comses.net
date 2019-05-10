import {detect} from 'detect-browser';
import Vue from 'vue';
import {Component, Prop} from 'vue-property-decorator';

const MIN_CHROME_VERSION = 59;

@Component({
    template: `<ul class="navbar-nav ml-auto">
        <li class="nav-item" v-if="!supported">
            <div class="alert alert-danger mb-0" v-if="browser">
                <span class='fa fa-warning'></span> {{ browser_warnings[browser.name] }}
            </div>
            <div class="alert alert-danger mb-0" v-else>
                <span class='fa fa-warning'></span> Browser is unsupported. Some site functionality may not work.
            </div>
        </li>
    </ul>`,
})
export class BrowserDetect extends Vue {
    public browser_warnings = {
        ie: 'All versions of Internet Explorer are unsupported. Some site functionality may not work.',
        chrome: `Chrome versions before ${MIN_CHROME_VERSION} are unsupported. Some site functionality may not work.`,
    };

    @Prop()
    public browser: any;

    get supported() {
        if (this.browser) {
            const version = parseInt(this.browser.version.split('.')[0]);
            if (this.browser.name === 'ie') {
                return false;
            } else if (this.browser.name === 'chrome' && version <= MIN_CHROME_VERSION) {
                return false;
            }
        }
        return true;
    }
}

new BrowserDetect({propsData: {browser: detect()}}).$mount('#browser-message');
