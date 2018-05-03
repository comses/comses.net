const path = require('path');
const stringify = require('stringify-object');

const webpack = require('webpack');
const {
    createConfig, match, entryPoint, setOutput, addPlugins,
    customConfig, defineConstants, env, sourceMaps
} = require('webpack-blocks');
const { url, file } = require('@webpack-blocks/assets');
const typescript = require('@webpack-blocks/typescript');
const sass = require('@webpack-blocks/sass');
const extractText = require('@webpack-blocks/extract-text');
const BundleTracker = require('webpack-bundle-tracker');
const CompressionWebpackPlugin = require('compression-webpack-plugin');
const { TsConfigPathsPlugin } = require('awesome-typescript-loader');

function aliases(connectionFileName, handlerFileName) {
    return customConfig({
        resolve: {
            modules: [
                'src',
                'node_modules'
            ],
            alias: {
                'Marked': 'marked',
                'SimpleMDE': 'simplemde',
                'connection$': path.resolve(__dirname, 'src/api/' + connectionFileName),
                'handler$': path.resolve(__dirname, 'src/api/' + handlerFileName),
                'vue$': 'vue/dist/vue.common.js',
                'api': path.resolve(__dirname, 'src/api'),
                'pages': path.resolve(__dirname, 'src/pages'),
                'assets': path.resolve(__dirname, 'src/assets'),
                'store': path.resolve(__dirname, 'src/store'),
                'components': path.resolve(__dirname, 'src/components'),
                'util': path.resolve(__dirname, 'src/util'),
            }
        }
    })
}

function image(options) {
    return (context, {addLoader}) => {
        return addLoader({
            ...context.match,
            use: [
                {
                    loader: 'image-webpack-loader',
                    options: {
                        optipng: {
                            optimizationLevel: 5,
                        },
                        pngquant: {
                            quality: '100',
                        },
                        mozjpeg: {
                            quality: 100,
                        },
                        ...options,
                    }
                }
            ]
        })
    };
}

module.exports = createConfig([
    entryPoint({
        common: './src/common',
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
        styles: './src/styles/index.scss',
        vendors: './src/vendors.ts'
    }),
    setOutput({
        path: '/shared/webpack',
        filename: 'js/[name].[chunkhash].js',
        publicPath: '/static/'
    }),
    match('*.scss', { exclude: path.resolve('node_modules') }, [
        sass(),
        extractText('[name]-[contenthash:8].css')
    ]),
    match(/\.(png|jpe?g|gif|svg)(\?.*)?$/, [
        file({
            name: 'img/[name].[hash:7].[ext]'
        }),
        image()
    ]),
    match(/\.(woff2?|eot|ttf|otf)(\?.*)?$/, [
        url({
            limit: 50000,
            mimetype: 'application/font-woff',
            name: 'fonts/[name].[hash:7].[ext]'
        })
    ]),
    addPlugins([
        new webpack.ProvidePlugin({
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
        }),
        // split vendor js into its own file
        new webpack.optimize.CommonsChunkPlugin({
            name: 'vendors'
        }),
        // extract webpack runtime and module manifest to its own file in order to
        // prevent vendor hash from being updated whenever app bundle is updated
        new webpack.optimize.CommonsChunkPlugin({
            name: 'manifest',
            chunks: ['vendors']
        }),
        new BundleTracker({ path: '/shared/webpack', filename: './webpack-stats.json' })
    ]),
    sourceMaps('source-map'),
    defineConstants({
        'process.env.NODE_ENV': process.env.NODE_ENV,
        'window.__BASE_URL__': process.env.BASE_URL
    }),
    env('development', [
        aliases('connection.ts', 'handler.ts'),
        typescript(),
    ]),
    env('production', [
        aliases('connection.ts', 'handler.ts'),
        typescript(),
        addPlugins([
            new webpack.optimize.UglifyJsPlugin({
                parallel: true,
                sourceMap: true,
                compress: {
                    warnings: false
                }
            }),
            new webpack.LoaderOptionsPlugin({ minimize: true }),
            new webpack.optimize.OccurrenceOrderPlugin(),
            new CompressionWebpackPlugin({
                asset: '[path].gz[query]',
                algorithm: 'gzip',
                test: new RegExp(
                    '\\.(' +
                    ['js', 'css'].join('|') +
                    ')$'
                ),
                threshold: 10240,
                minRatio: 0.8
            })
        ])
    ]),
    env('testing',  [
        aliases('mock_connection.ts', 'mock_handler.ts'),
        typescript({configFileName: 'tsconfig_test.json'}),
    ])
]);

console.log(stringify({ resolve: module.exports.resolve, module: module.exports.module }))
