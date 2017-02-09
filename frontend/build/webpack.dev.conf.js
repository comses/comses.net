var config = require('../config')
var webpack = require('webpack')
var merge = require('webpack-merge')
var utils = require('./utils')
var baseWebpackConfig = require('./webpack.base.conf')
var BundleTracker = require('webpack-bundle-tracker')

module.exports = merge(baseWebpackConfig, {
    output: {
        filename: utils.assetsPath('js/[name].[chunkhash].js'),
        chunkFilename: utils.assetsPath('js/[id].[chunkhash].js')
    },
    module: {
        rules: utils.styleLoaders({sourceMap: config.dev.cssSourceMap})
    },
    devServer: {
        historyApiFallback: true,
        noInfo: true
    },
    // eval-source-map is faster for development
    devtool: '#eval-source-map',
    plugins: [
        new BundleTracker({path: '/webpack', filename: './webpack-stats.json'}),
        new webpack.DefinePlugin({
            'process.env': config.dev.env
        }),
        // https://github.com/glenjamin/webpack-hot-middleware#installation--usage
        //new webpack.optimize.OccurenceOrderPlugin(),
        new webpack.NoEmitOnErrorsPlugin(),
    ]
});
