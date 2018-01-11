const webpack = require('webpack');

const externalWebpackConfig = require('./webpack.conf');
const webpackConfig = {};
webpackConfig['module'] = externalWebpackConfig['module'];
webpackConfig['resolve'] = externalWebpackConfig['resolve'];
webpackConfig['plugins'] = externalWebpackConfig['plugins'];
webpackConfig['devtool'] = 'inline-source-map';
console.log(webpackConfig.plugins[7].definitions);

module.exports = function(config) {
    config.set({
        files: [
           {pattern: 'src/**/*.ts', watched: false}
        ],
        frameworks: ['jasmine'],
        preprocessors: {
           'src/**/*.spec.ts': ['webpack', 'sourcemap']
        },
        webpack: webpackConfig,
        client: {
           captureConsole: false
        },
        reporters: ['dots'],

        port: 9876,
        colors: true
    });
};