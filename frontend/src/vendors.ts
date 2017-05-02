declare const require: {
    <T>(path: string): T;
    (paths: string[], callback: (...modules: any[]) => void): void;
    ensure: (paths: string[], callback: (require: <T>(path: string) => T) => void) => void;
};

import 'bootstrap'
import 'vue'
import 'lodash';
import 'vue-multiselect'
import 'vue-property-decorator'
import 'ajv'
import 'query-string'

// Make jQuery and $ globals on window
require('expose-loader?$!jquery');
require('expose-loader?jQuery!jquery');
