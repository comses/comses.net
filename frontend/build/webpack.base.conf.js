var path = require('path')
var config = require('../config')
var utils = require('./utils')
var projectRoot = path.resolve(__dirname, '../')
var webpack = require('webpack')

var env = process.env.NODE_ENV
// check env & config/index.js to decide weither to enable CSS Sourcemaps for the
// various preprocessor loaders added to vue-loader at the end of this file
var cssSourceMapDev = (env === 'development' && config.dev.cssSourceMap)
var cssSourceMapProd = (env === 'production' && config.build.productionSourceMap)
var useCssSourceMap = cssSourceMapDev || cssSourceMapProd

module.exports = {
    entry: {
        home: './src/pages/home/home.ts',
        vendors: './src/vendors.js',
        styles: './src/style.scss'
    },
    output: {
        path: config.build.assetsRoot,
        filename: utils.assetsPath('js/[name].[chunkhash].js'),
        chunkFilename: utils.assetsPath('js/[id].[chunkhash].js'),
        publicPath: process.env.NODE_ENV === 'production' ? config.build.assetsPublicPath : config.dev.assetsPublicPath,
    },
    resolve: {
        extensions: ['.js', '.vue', '.ts'],
        modules: [
            path.join(projectRoot, 'src'),
            path.join(projectRoot, 'node_modules')
        ],
        alias: {
            'vue$': 'vue/dist/vue.common.js',
            'src': path.resolve(__dirname, '../src'),
            'pages': path.resolve(__dirname, '../src/pages'),
            'assets': path.resolve(__dirname, '../src/assets'),
            'store': path.resolve(__dirname, '../src/store'),
            'components': path.resolve(__dirname, '../src/components')
        }
    },
    resolveLoader: {
        modules: [path.join(__dirname, '../node_modules')]
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loaders: 'vue-loader',
                options: {
                    loaders: {
                        ts: 'ts-loader',
                        scss: utils.extractSCSS.extract({
                            // fallback: 'vue-style-loader',
                            use: ['css-loader', 'sass-loader']
                        })
                    },
                    esModule: true,
                    extract: true,
                    postcss: [
                        require('autoprefixer')({
                            browsers: ['last 2 versions']
                        })
                    ]
                }
            },
            {
                test: /\.ts$/,
                loader: 'ts-loader',
                include: projectRoot,
                exclude: /node_modules/,
                options: {
                    // 5. Append a ".ts" file to all ".vue" file so typescript can preprocess the file
                    appendTsSuffixTo: [/\.vue$/]
                }
            },
            {
                test: /\.(png|jpe?g|gif|svg)(\?.*)?$/,
                loader: 'url-loader',
                query: {
                    limit: 10000,
                    name: utils.assetsPath('img/[name].[hash:7].[ext]')
                }
            },
            {
                test: /\.(woff2?|eot|ttf|otf)(\?.*)?$/,
                loader: 'url-loader',
                options: {
                    limit: 10000,
                    name: utils.assetsPath('fonts/[name].[hash:7].[ext]')
                }
            }
        ]
    },
    plugins: [
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            "window.jQuery": "jquery",
            Tether: "tether",
            "window.Tether": "tether",
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
        }),
        utils.extractSCSS,
        // split vendor js into its own file
        new webpack.optimize.CommonsChunkPlugin({
            name: 'vendors'
        }),
        // extract webpack runtime and module manifest to its own file in order to
        // prevent vendor hash from being updated whenever app bundle is updated
        new webpack.optimize.CommonsChunkPlugin({
            name: 'manifest',
            chunks: ['vendors']
        })
    ]
};
