import * as Vue from 'vue'
import Component from 'vue-class-component'

@Component({
    template: `<section class="carousel">
        <h1> {{ heading }}</h1>
        <h4 v-if="subheading !== ''"> {{ subheading }}</h4>
    </section>`,
    props: {
        heading: String,
        subheading: String
    }
})
class SubHeader extends Vue {

}

export default SubHeader