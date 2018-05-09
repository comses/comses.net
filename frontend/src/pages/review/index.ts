import {EditorReviewDetail} from "./edit";

function extractParams() {
    const el = document.getElementById('app');
    const review_uuid = el.getAttribute('data-review-uuid');
    const status_levels = JSON.parse(el.getAttribute('data-status-levels'));
    return {review_uuid, status_levels};
}

new EditorReviewDetail({propsData: extractParams()}).$mount('#app');