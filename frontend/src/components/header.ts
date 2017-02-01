import * as Vue from 'vue'
import Component from 'vue-class-component'

@Component({
    template: `<header class="fixed-top">
        <div class="container">
            <div class="row">
                <div class="col-sm-12 col-md-6 col-lg-4">
                    <nav class="nav">
                        <router-link :to="{ name: 'home' }" class="nav-link">
                            <span class="logo">CoMSES Network | OpenABM</span>
                        </router-link>          
                    </nav>
                </div>
                <div class="col-sm-12 col-md-6 col-lg-8">
                    <nav class="nav justify-content-end">
                        <router-link :to="{ name: 'codebase_list' }" class="nav-link">Model Library</router-link>
                        <router-link :to="{ name: 'event_list' }" class="nav-link">Events</router-link>
                        <router-link :to="{ name: 'job_list' }" class="nav-link">Jobs</router-link>
                        <router-link :to="{ name: 'resource_list' }" class="nav-link">Resources</router-link>
                        <a class="fa fa-search nav-link" href="#"></a>
                        <a class= "fa fa-chevron-down nav-link" href="#"></a>
                    </nav>
                </div>
            </div>
        </div>
    </header>`
})
class Header extends Vue {

}

export default Header
