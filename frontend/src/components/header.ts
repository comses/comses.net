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
                    <ul class="nav justify-content-end">
                        <li class="nav-item">
                            <router-link :to="{ name: 'codebase_list' }" class="nav-link">Model Library</router-link>
                        </li>
                        <li class="nav-item">
                            <router-link :to="{ name: 'event_list' }" class="nav-link">Events</router-link>
                        </li>
                        <li>
                            <router-link :to="{ name: 'job_list' }" class="nav-link">Jobs</router-link>
                        </li>
                        <li class="nav-item">
                            <router-link :to="{ name: 'resource_list' }" class="nav-link">Resources</router-link>
                        </li>
                        <li class="nav-item">
                            <a class="fa fa-search nav-link" href="#"></a>
                        </li>
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" data-toggle="dropdown" role="button" href="#" aria-haspopup="true" aria-expanded="true">
                                <span class="fa fa-chevron-down"></span>
                            </a>
                            <div class="dropdown-menu">
                                <a class="dropdown-item" href="#">Log In</a>
                                <a class="dropdown-item" href="#">Log Out</a>
                                <a class="dropdown-item" href="#">Profile</a>
                            </div> 
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </header>`
})
class Header extends Vue {
    get loggedIn(): boolean {
        return this.$store.state.account.loggedIn;
    }

    // need to track whether or not we are currently logged in
    // logged in -> log out, profile
    // not logged in -> log in
}

export default Header
