import {EditorReviewDetail} from "./edit";

function extractParams() {
    const el = document.getElementById('app');
    const review_slug = el.getAttribute('data-review-slug');
    const status_levels = JSON.parse(el.getAttribute('data-status-levels'));
    const status = el.getAttribute('data-status');
    const event_list_url = el.getAttribute('data-event-list-url');
    return {props: {review_slug, status_levels, event_list_url}, data: {status}};
}

const {props, data} = extractParams();
const component = new EditorReviewDetail({propsData: props}).$mount('#app');
component.status = data.status;