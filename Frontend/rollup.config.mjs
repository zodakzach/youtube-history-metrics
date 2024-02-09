// rollup.config.mjs
import nodeResolve from '@rollup/plugin-node-resolve';

export default {
	input: 'static/js/main.js',
	output: {
		file: 'static/js/bundle.js',
		format: 'es'
	},
    plugins: [nodeResolve()]
};