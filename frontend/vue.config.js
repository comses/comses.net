const BundleTracker = require('webpack-bundle-tracker');
const webpack = require('webpack');
const _ = require('lodash');
const path = require('path');
const ini = require('ini');
const fs = require('fs');

const projectSettings = ini.decode(fs.readFileSync('/secrets/config.ini', 'utf8'));

function addStyleResource(rule) {
    rule.use('style-resource')
        .loader('style-resources-loader')
        .options({
            patterns: [
                path.resolve(__dirname, './src/styles/index.scss'),
            ],
        })
}

const pages = {
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
};

module.exports = {
    configureWebpack: {
      devtool: 'source-map',
      mode: 'development',
      plugins: [
	new BundleTracker({ filename: '/shared/webpack/webpack-stats.json' }),
      ],
    },
    chainWebpack: config => {
        const types = ['vue-modules', 'vue', 'normal-modules', 'normal'];
        types.forEach(type => addStyleResource(config.module.rule('scss').oneOf(type)));

        config
            .output
            .filename('js/[name].[hash].js');
	    /*
        config
            .plugin('bundle-tracker')
            .use(BundleTracker, [{path: '/shared/webpack', filename: './webpack-stats.json'}])
            .end();
	    */
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

        config
            .plugin('define-sentry')
            .use(webpack.DefinePlugin, [{
                'process.env.SENTRY_DSN': JSON.stringify(projectSettings.logging.SENTRY_DSN)
            }]);

        config.devServer
            .public('http://0.0.0.0:3000')
            .host('0.0.0.0')
            .port(3000)
            .hotOnly(true)
            .watchOptions({poll: 1000})
            .https(false)
            .headers({"Access-Control-Allow-Origin": ["\*"]});

        return config;
    },
    css: {
        extract: true
    },
    outputDir: '/shared/webpack',
    pages: {
        home: 'src/pages/home.vue',
        codebase_list: './src/pages/codebase/list.ts',
        event_calendar: './src/pages/event/calendar.ts',
        event_list: './src/pages/event/list.ts',
        job_list: './src/pages/job/list.ts',
        profile_list: './src/pages/profile/list.ts',
        codebases: './src/pages/codebase',
        events: './src/pages/event',
        jobs: './src/pages/job',
        profiles: './src/pages/profile',
        releases: './src/pages/codebase/release',
        reviews: './src/pages/review',
        release_regenerate_share_uuid: './src/pages/codebase/release/regenerate_share_uuid.ts'
    },
    publicPath: process.env.NODE_ENV === 'development' ? 'http://localhost:3000/static/' : '/static/',
    runtimeCompiler: true
};
