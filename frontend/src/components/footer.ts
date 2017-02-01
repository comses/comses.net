import * as Vue from 'vue'
import Component from 'vue-class-component'

@Component({
    template: `<footer class="footer">
            <div class="container">
                <div class="row">
                    <div class="col-xs-12 col-lg-3">
                        <ul class="nav social-media">
                            <li class="nav-item">
                                <a href="https://github.com/comses" title="GitHub" target="_blank">
                                <span class="fa-stack">
                                  <i class="fa fa-circle fa-stack-2x"></i>
                                  <i class="fa fa-code-fork fa-inverse fa-stack-1x"></i>
                                </span>
                                </a>
                            </li>
                            <li class="nav-item">
                                <a href="https://twitter.com/openabm_comses" title="Twitter" target="_blank">
                                  <span class="fa-stack">
                                    <i class="fa fa-circle fa-stack-2x"></i>
                                    <i class="fa fa-twitter fa-inverse fa-stack-1x"></i>
                                  </span>
                                </a>
                            </li>

                            <!--
                            <li>
                              <a href="http://www.openabm.org/rss.xml" title="RSS Feed">
                                <span class="fa-stack">
                                  <i class="fa fa-circle fa-stack-2x"></i>
                                  <i class="fa fa-rss fa-inverse fa-stack-1x"></i>
                                </span>
                              </a>
                            </li>
                            -->

                            <li>
                                <a href="http://eepurl.com/b8GCUv" title="Email Sign Up" target="_blank">
                                  <span class="fa-stack">
                                    <i class="fa fa-circle fa-stack-2x"></i>
                                    <i class="fa fa-envelope fa-inverse fa-stack-1x"></i>
                                  </span>
                                </a>
                            </li>
                        </ul>
                    </div>

                    <div class="col-xs-12 col-lg-9">
                        <ul class="organizations">
                            <li>
                                <a href="http://www.asu.edu/" target="_blank">
                                    <img src="/static/images/logo-asu.png" alt="Arizona State University">
                                </a>
                            </li>

                            <li>
                                <a href="https://creativecommons.org/" target="_blank">
                                    <img src="/static/images/logo-cc.png" alt="Creative Commons">
                                </a>
                            </li>

                            <li>
                                <a href="http://www.nsf.gov/" target="_blank">
                                    <img src="/static/images/logo-nsf.png" alt="National Science Foundation">
                                </a>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <p class="copyright text-center">© 2016 CoMSES Net</p>
        </footer>`
})
class Footer extends Vue {

}

export default Footer
