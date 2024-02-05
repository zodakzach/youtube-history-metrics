// postcss.config.js
module.exports = {
    plugins: [
      require('tailwindcss')('tailwindcss/tailwind.config.js'),
      require('@tailwindcss/forms'),
      require('@tailwindcss/typography'),
      require('autoprefixer'),
    ],
  };
  