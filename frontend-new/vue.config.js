const BundleTracker = require('webpack-bundle-tracker');
const webpack = require('webpack');

module.exports = {
    chainWebpack: config => {
        config
            .output
            .filename('js/[name].[hash].js');
        config
            .plugin('bundle-tracker')
            .use(BundleTracker, [{path: '/shared/webpack', filename: './webpack-stats.json'}])
            .end();
        config
            .plugin('provide-bootstrap')
            .use(webpack.ProvidePlugin, [{
                $: "jquery",
                jQuery: "jquery",
                "window.jQuery": "jquery",
                Popper: ['popper.js', 'default'],
                Alert: "exports-loader?Alert!bootstrap/js/dist/alert",
                Button: "exports-loader?Button!bootstrap/js/dist/button",
                Carousel: "exports-loader?Carousel!bootstrap/js/dist/carousel",
                Collapse: "exports-loader?Collapse!bootstrap/js/dist/collapse",
                Dropdown: "exports-loader?Dropdown!bootstrap/js/dist/dropdown",
                Modal: "exports-loader?Modal!bootstrap/js/dist/modal",
                Popover: "exports-loader?Popover!bootstrap/js/dist/popover",
                Scrollspy: "exports-loader?Scrollspy!bootstrap/js/dist/scrollspy",
                Tab: "exports-loader?Tab!bootstrap/js/dist/tab",
                Tooltip: "exports-loader?Tooltip!bootstrap/js/dist/tooltip",
                Util: "exports-loader?Util!bootstrap/js/dist/util",
            }]);
        return config;
    },
    outputDir: '/shared/webpack',
    pages: {
        codebases: './src/pages/codebase',
        events: './src/pages/event',
        jobs: './src/pages/job',
        profiles: './src/pages/profile',
        reviews: './src/pages/review',
        releases: './src/pages/codebase/release',
        release_regenerate_share_uuid: './src/pages/codebase/release/regenerate_share_uuid.ts',
        codebase_list: './src/pages/codebase/list.ts',
        event_calendar: './src/pages/event/calendar.ts',
        event_list: './src/pages/event/list.ts',
        job_list: './src/pages/job/list.ts',
        profile_list: './src/pages/profile/list.ts',
    },
    publicPath: '/static/',
    runtimeCompiler: true
};
