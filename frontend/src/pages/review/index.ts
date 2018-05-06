import {EditorReviewDetail} from "./edit";

function extractParams() {
    const el = document.getElementById('app');
    const review_uuid = el.getAttribute('data-review-uuid');
    return {review_uuid};
}

new EditorReviewDetail({propsData: extractParams()}).$mount('#app');