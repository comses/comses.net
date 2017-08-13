import * as Vue from 'vue'
import Component from 'vue-class-component'

@Component({
    template: `<div>
        <span v-for="tag in tags" class="p-2 m-1 badge badge-primary">{{ tag.name }}</span>
    </div>`,
    props: ['tags']
})
class TagList extends Vue {}

export default TagList;