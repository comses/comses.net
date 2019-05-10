import Popper from 'popper.js';
// This window hack is temporary https://stackoverflow.com/questions/45645971/bootstrap-4-beta-importing-popper-js-with-webpack-3-x-throws-popper-is-not-a-con
(window as any).Popper = Popper;
import 'bootstrap';
import 'lodash';
import 'query-string';
import 'vue';
import 'vuedraggable';
import 'vue-multiselect';
import 'vue-property-decorator';
import 'vue-router';
import 'vuex';
import 'yup';
